from dataclasses import dataclass
from typing import Any, Protocol

from agentgw.domain.delivery.entities import Delivery
from agentgw.domain.delivery.repositories import DeliveryRepository
from agentgw.domain.message.entities import ChannelMessage
from agentgw.domain.message.repositories import MessageRepository
from agentgw.domain.sync.repositories import SyncRepository


@dataclass
class SyncMessagesResult:
    synced_count: int
    next_cursor: dict[str, Any]


class ChannelClient(Protocol):
    async def fetch_messages(self, account_id: str, cursor_payload: dict[str, Any]) -> tuple[list[ChannelMessage], dict[str, Any]]:
        raise NotImplementedError


class SyncMessagesService:
    def __init__(
        self,
        channel_client: ChannelClient,
        cursor_repository: SyncRepository,
        message_repository: MessageRepository,
        delivery_repository: DeliveryRepository,
    ):
        self._channel_client = channel_client
        self._cursor_repository = cursor_repository
        self._message_repository = message_repository
        self._delivery_repository = delivery_repository

    async def sync_account(self, account_id: str, channel_type: str) -> SyncMessagesResult:
        cursor = await self._cursor_repository.get_for_scope(account_id, channel_type, "messages")
        cursor_payload = cursor.cursor_payload if cursor else {}
        messages, next_cursor = await self._channel_client.fetch_messages(account_id, cursor_payload)

        for message in messages:
            await self._message_repository.save(message)
            await self._delivery_repository.save(self._build_delivery(account_id, channel_type, message))

        await self._cursor_repository.upsert(account_id, channel_type, "messages", next_cursor)
        return SyncMessagesResult(synced_count=len(messages), next_cursor=next_cursor)

    @staticmethod
    def _build_delivery(account_id: str, channel_type: str, message: ChannelMessage) -> Delivery:
        return Delivery(
            delivery_id=f"{channel_type}:{account_id}:{message.message_id}",
            message_id=message.message_id,
        )
