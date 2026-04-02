import json

import pytest

from agentgw.domain.agent.contracts import SendMessageRequest
from agentgw.infrastructure.providers.agent_ws import provider as provider_module
from agentgw.infrastructure.providers.agent_ws.provider import WebSocketAgentProvider


class FakeWebSocket:
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.sent_payloads: list[str] = []
        self.closed = False

    async def send(self, payload: str) -> None:
        self.sent_payloads.append(payload)

    async def recv(self) -> str:
        return self._responses.pop(0)


class FakeConnectionContext:
    def __init__(self, websocket: FakeWebSocket):
        self.websocket = websocket
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(self) -> FakeWebSocket:
        self.enter_count += 1
        return self.websocket

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exit_count += 1
        self.websocket.closed = True


class FakeConnectFactory:
    def __init__(self, responses: list[str]):
        self.calls = 0
        self.websocket = FakeWebSocket(responses)
        self.contexts: list[FakeConnectionContext] = []

    def __call__(self, url: str, open_timeout: int, close_timeout: int) -> FakeConnectionContext:
        self.calls += 1
        context = FakeConnectionContext(self.websocket)
        self.contexts.append(context)
        return context


@pytest.mark.asyncio
async def test_send_message_frames_request_and_reuses_connection(monkeypatch) -> None:
    request = SendMessageRequest(
        request_id="req-1",
        channel_type="wecom",
        tenant_id="tenant-1",
        message_id="msg-1",
        sender_id="user-1",
        conversation_id="conv-1",
        content="hello",
    )
    factory = FakeConnectFactory(
        [
            json.dumps(
                {
                    "type": "send_message_result",
                    "request_id": "req-1",
                    "provider_message_id": "agent-1",
                    "content": "reply-1",
                }
            ),
            json.dumps(
                {
                    "type": "send_message_result",
                    "request_id": "req-1",
                    "provider_message_id": "agent-2",
                    "content": "reply-2",
                }
            ),
        ]
    )
    recorded_timeouts: list[int] = []

    async def fake_wait_for(awaitable, timeout):
        recorded_timeouts.append(timeout)
        return await awaitable

    monkeypatch.setattr(provider_module.asyncio, "wait_for", fake_wait_for)

    provider = WebSocketAgentProvider(
        ws_url="ws://agent",
        timeout_seconds=7,
        connect_factory=factory,
    )

    first = await provider.send_message(request)
    second = await provider.send_message(request)

    assert factory.calls == 1
    assert factory.contexts[0].enter_count == 1
    assert factory.contexts[0].exit_count == 0
    assert recorded_timeouts == [7, 7]
    assert first.provider_message_id == "agent-1"
    assert first.content == "reply-1"
    assert second.provider_message_id == "agent-2"
    assert second.content == "reply-2"
    assert [json.loads(payload) for payload in factory.websocket.sent_payloads] == [
        {
            "type": "send_message",
            "request_id": "req-1",
            "channel_type": "wecom",
            "tenant_id": "tenant-1",
            "message_id": "msg-1",
            "sender_id": "user-1",
            "conversation_id": "conv-1",
            "content": "hello",
            "metadata": {},
        },
        {
            "type": "send_message",
            "request_id": "req-1",
            "channel_type": "wecom",
            "tenant_id": "tenant-1",
            "message_id": "msg-1",
            "sender_id": "user-1",
            "conversation_id": "conv-1",
            "content": "hello",
            "metadata": {},
        },
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_payload",
    [
        {
            "type": "send_message_error",
            "request_id": "req-1",
            "error_code": "agent_timeout",
            "error_message": "timed out",
        },
        {
            "type": "send_message_result",
            "request_id": "other",
            "provider_message_id": "agent-1",
            "content": "reply",
        },
    ],
)
async def test_send_message_rejects_invalid_response_frames(response_payload) -> None:
    request = SendMessageRequest(
        request_id="req-1",
        channel_type="wecom",
        tenant_id="tenant-1",
        message_id="msg-1",
        sender_id="user-1",
        conversation_id="conv-1",
        content="hello",
    )
    factory = FakeConnectFactory([json.dumps(response_payload)])
    provider = WebSocketAgentProvider(
        ws_url="ws://agent",
        timeout_seconds=7,
        connect_factory=factory,
    )

    with pytest.raises(ValueError):
        await provider.send_message(request)

    assert factory.calls == 1
    assert factory.contexts[0].exit_count == 1
