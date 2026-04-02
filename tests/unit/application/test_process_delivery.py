import pytest

from agentgw.application.dto.messages import SendMessageResponse
from agentgw.application.services.process_delivery import ProcessDeliveryService
from agentgw.domain.delivery.entities import Delivery, DeliveryStatus
from agentgw.domain.message.entities import ChannelMessage


class FakeAgentProvider:
    async def send_message(self, request):
        return SendMessageResponse(provider_message_id="p-1", content="reply")


class FakeMessageRepository:
    async def get_by_message_id(self, message_id: str) -> ChannelMessage:
        return ChannelMessage(
            message_id=message_id,
            channel_type="wecom",
            account_id="tenant-1",
            conversation_id="conv-1",
            sender_id="user-1",
            sender_is_internal=False,
            content="hello",
            sent_at=__import__("datetime").datetime.now(),
            raw_payload={},
        )


class FakeDeliveryRepository:
    def __init__(self):
        self.saved_delivery: Delivery | None = None

    async def save(self, delivery: Delivery) -> Delivery:
        self.saved_delivery = delivery
        return delivery


@pytest.mark.asyncio
async def test_process_delivery_marks_success() -> None:
    delivery = Delivery.create(message_id="msg-1")
    delivery.mark_routed("agent-1")
    delivery.status = DeliveryStatus.DISPATCHED

    delivery_repository = FakeDeliveryRepository()
    service = ProcessDeliveryService(
        agent_provider=FakeAgentProvider(),
        message_repository=FakeMessageRepository(),
        delivery_repository=delivery_repository,
    )

    updated = await service.process(delivery)

    assert updated.status is DeliveryStatus.SUCCEEDED
    assert updated.reply_content == "reply"
    assert delivery_repository.saved_delivery is updated
