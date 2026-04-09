from __future__ import annotations

from types import SimpleNamespace

import pytest

from agentgw.domain.agent.entities import AgentEndpoint
from agentgw.infrastructure.providers import agent_factory as agent_factory_module
from agentgw.infrastructure.providers.agent_sdk.relay_bridge import RelaySdkBridge
from agentgw.infrastructure.providers.agent_sdk.loader import load_relay_sdk_client, load_relay_sdk_event_type
from agentgw.infrastructure.providers.agent_sdk.session import RelaySdkAgentSession


class FakeEventType:
    AGENT_CALL = "AGENT_CALL"
    AGENT = "AGENT"
    TOOL_EXECUTION = "TOOL_EXECUTION"


class FakeClient:
    def __init__(self) -> None:
        self.handlers: dict[str, object] = {}
        self.connected = False
        self.sent_config: dict[str, object] | None = None
        self.sent_message: str | None = None
        self.waited = False
        self.closed = False

    def on(self, event_key: str):
        def decorator(handler):
            self.handlers[event_key] = handler
            return handler

        return decorator

    async def __aenter__(self):
        self.connected = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.closed = True
        self.connected = False

    async def send_config(self, config: dict[str, object]) -> None:
        self.sent_config = config

    async def send_message(self, message: str) -> None:
        self.sent_message = message
        await self.handlers[FakeEventType.AGENT_CALL](SimpleNamespace(agent_name="assistant", is_start=True))
        await self.handlers[FakeEventType.AGENT](SimpleNamespace(content="hello from agent"))
        await self.handlers[FakeEventType.TOOL_EXECUTION](
            SimpleNamespace(tool_name="search", is_start=False, result_summary="ok")
        )

    async def wait_until_done(self) -> None:
        self.waited = True


@pytest.mark.asyncio
async def test_relay_bridge_emits_normalized_sse_events() -> None:
    client = FakeClient()
    bridge = RelaySdkBridge(
        ws_url="ws://relay",
        message="hello",
        project_home="/tmp/project",
        timeout_seconds=1,
        client=client,
        event_type=FakeEventType,
    )

    await bridge.relay_worker()

    items: list[tuple[str, dict[str, object]] | tuple[str, str]] = []
    while not bridge.queue.empty():
        items.append(await bridge.queue.get())

    assert client.connected is False
    assert client.closed is True
    assert client.sent_config == {"project_home": "/tmp/project"}
    assert client.sent_message == "hello"
    assert client.waited is True
    assert items == [
        ("debug", {"step": "connecting", "ws_url": "ws://relay"}),
        ("debug", {"step": "connected"}),
        ("debug", {"step": "config_sent", "project_home": "/tmp/project"}),
        ("agent_call", {"agent_name": "assistant", "is_start": True}),
        ("agent_text", {"content": "hello from agent"}),
        ("tool", {"tool_name": "search", "is_start": False, "result_summary": "ok"}),
        ("debug", {"step": "message_sent", "message": "hello"}),
        ("done", {"status": "completed"}),
    ]


def test_build_agent_transport_uses_relay_sdk_loader_from_endpoint_config(monkeypatch) -> None:
    endpoint = AgentEndpoint(
        endpoint_id="endpoint-1",
        endpoint_type="relay_sdk",
        base_url="ws://relay",
        auth_config={
            "relay_sdk_module": "custom_sdk",
            "relay_sdk_client_class": "RelayClient",
        },
        timeout_seconds=30,
    )
    fake_client = object()
    calls: list[tuple[str, str, str]] = []

    def fake_loader(ws_url: str, *, module_path: str = "your_sdk", client_class_name: str = "RelayClient"):
        calls.append((ws_url, module_path, client_class_name))
        return fake_client

    monkeypatch.setattr(agent_factory_module, "load_relay_sdk_client", fake_loader)

    session = agent_factory_module.build_agent_transport(endpoint)

    assert isinstance(session, RelaySdkAgentSession)
    assert session._client is fake_client
    assert calls == [("ws://relay", "custom_sdk", "RelayClient")]


def test_loader_imports_relay_sdk_symbols(monkeypatch) -> None:
    class RelayClient:
        def __init__(self, ws_url: str) -> None:
            self.ws_url = ws_url

    event_type = object()
    module = SimpleNamespace(RelayClient=RelayClient, EventType=event_type)
    monkeypatch.setattr("agentgw.infrastructure.providers.agent_sdk.loader.import_module", lambda _: module)

    client = load_relay_sdk_client("ws://relay", module_path="custom_sdk", client_class_name="RelayClient")
    assert isinstance(client, RelayClient)
    assert client.ws_url == "ws://relay"
    assert load_relay_sdk_event_type(module_path="custom_sdk", enum_name="EventType") is event_type
