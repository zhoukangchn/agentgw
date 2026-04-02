from dataclasses import dataclass

from agentgw.domain.delivery.entities import Delivery


@dataclass
class SyncMessagesResult:
    synced_count: int
    next_cursor: dict


class SyncMessagesService:
    def __init__(self, channel_client, cursor_repository, message_repository, delivery_repository):
        self._channel_client = channel_client
        self._cursor_repository = cursor_repository
        self._message_repository = message_repository
        self._delivery_repository = delivery_repository

    async def sync_account(self, account_id: str) -> SyncMessagesResult:
        cursor = await self._cursor_repository.get_for_scope(account_id, "messages")
        messages, next_cursor = await self._channel_client.fetch_messages(
            account_id,
            cursor.cursor_payload if cursor else {},
        )

        for message in messages:
            await self._message_repository.save(message)
            await self._delivery_repository.save(Delivery.create(message.message_id))

        await self._cursor_repository.upsert(account_id, "messages", next_cursor)
        return SyncMessagesResult(synced_count=len(messages), next_cursor=next_cursor)
