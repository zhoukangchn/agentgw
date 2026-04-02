import pytest

from agentgw.application.services.sync_messages import SyncMessagesService
from agentgw.domain.delivery.entities import Delivery
from agentgw.domain.message.entities import ChannelMessage


class FakeChannelClient:
    async def fetch_messages(self, account_id: str, cursor_payload: dict) -> tuple[list[ChannelMessage], dict]:
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


class FakeCursor:
    def __init__(self, cursor_payload: dict):
        self.cursor_payload = cursor_payload


class FakeCursorRepository:
    def __init__(self):
        self.saved_payload: dict | None = None

    async def get_for_scope(self, account_id: str, scope: str) -> FakeCursor:
        return FakeCursor({"seq": 0})

    async def upsert(self, account_id: str, scope: str, payload: dict) -> None:
        self.saved_payload = payload


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

    result = await service.sync_account("acc-1")

    assert result.synced_count == 1
    assert result.next_cursor == {"seq": 10}
    assert cursor_repository.saved_payload == {"seq": 10}
    assert len(message_repository.saved_messages) == 1
    assert len(delivery_repository.saved_deliveries) == 1
