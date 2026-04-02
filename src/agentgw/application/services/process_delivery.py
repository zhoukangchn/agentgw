from agentgw.application.dto.messages import SendMessageRequest
from agentgw.domain.delivery.entities import Delivery


class ProcessDeliveryService:
    def __init__(self, agent_provider, message_repository, delivery_repository):
        self._agent_provider = agent_provider
        self._message_repository = message_repository
        self._delivery_repository = delivery_repository

    async def process(self, delivery: Delivery) -> Delivery:
        try:
            message = await self._message_repository.get_by_message_id(delivery.message_id)
            delivery.mark_dispatching()
            response = await self._agent_provider.send_message(
                SendMessageRequest(
                    request_id=delivery.delivery_id or delivery.message_id,
                    channel_type=message.channel_type,
                    tenant_id=message.account_id,
                    message_id=message.message_id,
                    sender_id=message.sender_id,
                    conversation_id=message.conversation_id,
                    content=message.content,
                )
            )
            delivery.mark_dispatched()
            delivery.mark_succeeded(response.content)
        except Exception as exc:
            delivery.mark_failed(str(exc))

        await self._delivery_repository.save(delivery)
        return delivery
