from typing import Any

import pytest

from agentgw.application.services.sync_messages import SyncMessagesService
from agentgw.domain.delivery.entities import Delivery
from agentgw.domain.message.entities import ChannelMessage
from agentgw.domain.sync.entities import SyncCursor


class FakeChannelClient:
    async def fetch_messages(
        self,
        account_id: str,
        cursor_payload: dict[str, Any],
    ) -> tuple[list[ChannelMessage], dict[str, Any]]:
        return (
            [
                ChannelMessage(
                    message_id="msg-1",
                    channel_type="wecom",
                    account_id=account_id,
                    conversation_id="conv-1",
                    sender_id="user-1",
                    sender_is_internal=False,
                    content="hello",
                    sent_at=__import__("datetime").datetime.now(),
                    raw_payload={},
                )
            ],
            {"seq": 10},
        )


class FakeCursorRepository:
    def __init__(self):
        self.saved_cursor: SyncCursor | None = None

    async def get_for_scope(self, account_id: str, channel_type: str, scope: str) -> SyncCursor | None:
        return SyncCursor(
            cursor_id=f"{channel_type}:{account_id}:{scope}",
            channel_type=channel_type,
            account_id=account_id,
            scope=scope,
            cursor_payload={"seq": 0},
        )

    async def upsert(
        self,
        account_id: str,
        channel_type: str,
        scope: str,
        payload: dict[str, Any],
    ) -> SyncCursor:
        self.saved_cursor = SyncCursor(
            cursor_id=f"{channel_type}:{account_id}:{scope}",
            channel_type=channel_type,
            account_id=account_id,
            scope=scope,
            cursor_payload=payload,
        )
        return self.saved_cursor


class FakeMessageRepository:
    def __init__(self):
        self.saved_messages: list[ChannelMessage] = []

    async def save(self, message: ChannelMessage) -> ChannelMessage:
        self.saved_messages.append(message)
        return message


class FakeDeliveryRepository:
    def __init__(self):
        self.saved_deliveries: list[Delivery] = []

    async def save(self, delivery: Delivery) -> Delivery:
        self.saved_deliveries.append(delivery)
        return delivery


class FakeIdempotentDeliveryRepository:
    def __init__(self):
        self.saved_deliveries: dict[str, Delivery] = {}

    async def save(self, delivery: Delivery) -> Delivery:
        if delivery.delivery_id is None:
            delivery.delivery_id = __import__("uuid").uuid4().hex
        self.saved_deliveries[delivery.delivery_id] = delivery
        return delivery


@pytest.mark.asyncio
async def test_sync_messages_persists_message_and_updates_cursor() -> None:
    cursor_repository = FakeCursorRepository()
    message_repository = FakeMessageRepository()
    delivery_repository = FakeDeliveryRepository()
    service = SyncMessagesService(
        channel_client=FakeChannelClient(),
        cursor_repository=cursor_repository,
        message_repository=message_repository,
        delivery_repository=delivery_repository,
    )

    result = await service.sync_account("acc-1", "wecom")

    assert result.synced_count == 1
    assert result.next_cursor == {"seq": 10}
    assert cursor_repository.saved_cursor is not None
    assert cursor_repository.saved_cursor.cursor_payload == {"seq": 10}
    assert len(message_repository.saved_messages) == 1
    assert len(delivery_repository.saved_deliveries) == 1


@pytest.mark.asyncio
async def test_sync_messages_reuses_delivery_identity_for_retries() -> None:
    cursor_repository = FakeCursorRepository()
    message_repository = FakeMessageRepository()
    delivery_repository = FakeIdempotentDeliveryRepository()
    service = SyncMessagesService(
        channel_client=FakeChannelClient(),
        cursor_repository=cursor_repository,
        message_repository=message_repository,
        delivery_repository=delivery_repository,
    )

    await service.sync_account("acc-1", "wecom")
    await service.sync_account("acc-1", "wecom")

    assert len(delivery_repository.saved_deliveries) == 1
