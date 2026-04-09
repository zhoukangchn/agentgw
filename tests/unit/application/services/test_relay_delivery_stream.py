from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from agentgw.application.services.relay_delivery_stream import RelayDeliveryStreamRequest, RelayDeliveryStreamService
from agentgw.domain.delivery.entities import Delivery, DeliveryStatus
from agentgw.domain.message.entities import ChannelMessage
from agentgw.infrastructure.config.settings import Settings


class FakeDeliveryRepository:
    def __init__(self, delivery: Delivery) -> None:
        self.delivery = delivery
        self.saved: list[Delivery] = []

    async def get_by_id(self, delivery_id: str) -> Delivery:
        assert delivery_id == self.delivery.delivery_id
        return self.delivery

    async def save(self, delivery: Delivery) -> Delivery:
        self.delivery = delivery
        self.saved.append(delivery)
        return delivery


class FakeMessageRepository:
    def __init__(self, message: ChannelMessage) -> None:
        self.message = message

    async def get_by_message_id(self, message_id: str) -> ChannelMessage:
        assert message_id == self.message.message_id
        return self.message


class FakeBridge:
    last_instance: "FakeBridge | None" = None

    def __init__(self, *, ws_url: str, message: str, project_home: str | None, timeout_seconds: int, client, event_type, event_sink) -> None:
        self.ws_url = ws_url
        self.message = message
        self.project_home = project_home
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.event_type = event_type
        self.event_sink = event_sink
        FakeBridge.last_instance = self

    async def stream(self, request):
        await self.event_sink("debug", {"step": "connecting", "ws_url": self.ws_url})
        yield "event: ready\ndata: {\"status\": \"ready\"}\n\n"
        await self.event_sink("debug", {"step": "connected"})
        await self.event_sink("debug", {"step": "config_sent", "project_home": self.project_home})
        await self.event_sink("debug", {"step": "message_sent", "message": self.message})
        await self.event_sink("agent_call", {"agent_name": "assistant", "is_start": True})
        await self.event_sink("agent_text", {"content": "hello"})
        yield "event: done\ndata: {\"status\": \"completed\"}\n\n"
        await self.event_sink("done", {"status": "completed"})


@pytest.mark.asyncio
async def test_stream_delivery_updates_delivery_state_and_emits_stream(monkeypatch) -> None:
    delivery = Delivery(
        delivery_id="delivery-1",
        message_id="message-1",
        agent_endpoint_id="relay_sdk",
        status=DeliveryStatus.ROUTED,
    )
    message = ChannelMessage(
        message_id="message-1",
        channel_type="wecom",
        account_id="account-1",
        conversation_id="conv-1",
        sender_id="sender-1",
        sender_is_internal=False,
        content="hello relay",
        sent_at=datetime.now(UTC),
        raw_payload={},
    )
    delivery_repo = FakeDeliveryRepository(delivery)
    message_repo = FakeMessageRepository(message)

    monkeypatch.setattr("agentgw.application.services.relay_delivery_stream.RelaySdkBridge", FakeBridge)
    monkeypatch.setattr("agentgw.application.services.relay_delivery_stream.load_relay_sdk_client", lambda *args, **kwargs: object())
    monkeypatch.setattr("agentgw.application.services.relay_delivery_stream.load_relay_sdk_event_type", lambda *args, **kwargs: SimpleNamespace())

    service = RelayDeliveryStreamService(
        settings=Settings(),
        message_repository=message_repo,
        delivery_repository=delivery_repo,
        client_factory=lambda *args, **kwargs: object(),
        event_type_loader=lambda *args, **kwargs: SimpleNamespace(),
    )

    request = RelayDeliveryStreamRequest(delivery_id="delivery-1", project_home="/tmp/project", timeout_seconds=2)
    async def is_disconnected() -> bool:
        return False

    request_wrapper = SimpleNamespace(is_disconnected=is_disconnected)

    chunks = []
    async for chunk in service.stream_delivery(request, request_wrapper):
        chunks.append(chunk)

    assert chunks[0].startswith("event: ready")
    assert chunks[-1].startswith("event: done")
    assert delivery_repo.delivery.status is DeliveryStatus.SUCCEEDED
    assert delivery_repo.delivery.reply_content == "hello"
    assert FakeBridge.last_instance is not None
    assert FakeBridge.last_instance.message == "hello relay"


@pytest.mark.asyncio
async def test_stream_delivery_routes_received_delivery(monkeypatch) -> None:
    delivery = Delivery(
        delivery_id="delivery-2",
        message_id="message-2",
        status=DeliveryStatus.RECEIVED,
    )
    message = ChannelMessage(
        message_id="message-2",
        channel_type="wecom",
        account_id="account-2",
        conversation_id="conv-2",
        sender_id="sender-2",
        sender_is_internal=False,
        content="hello relay",
        sent_at=datetime.now(UTC),
        raw_payload={},
    )
    delivery_repo = FakeDeliveryRepository(delivery)
    message_repo = FakeMessageRepository(message)

    monkeypatch.setattr("agentgw.application.services.relay_delivery_stream.RelaySdkBridge", FakeBridge)
    monkeypatch.setattr("agentgw.application.services.relay_delivery_stream.load_relay_sdk_client", lambda *args, **kwargs: object())
    monkeypatch.setattr("agentgw.application.services.relay_delivery_stream.load_relay_sdk_event_type", lambda *args, **kwargs: SimpleNamespace())

    service = RelayDeliveryStreamService(
        settings=Settings(),
        message_repository=message_repo,
        delivery_repository=delivery_repo,
        client_factory=lambda *args, **kwargs: object(),
        event_type_loader=lambda *args, **kwargs: SimpleNamespace(),
    )

    request = RelayDeliveryStreamRequest(delivery_id="delivery-2")
    async def is_disconnected() -> bool:
        return False

    request_wrapper = SimpleNamespace(is_disconnected=is_disconnected)

    chunks = []
    async for chunk in service.stream_delivery(request, request_wrapper):
        chunks.append(chunk)

    assert chunks
    assert delivery_repo.delivery.status is DeliveryStatus.SUCCEEDED
    assert delivery_repo.delivery.agent_endpoint_id == "relay_sdk"
