from dataclasses import dataclass
from typing import Any, Protocol

from agentgw.domain.contact.entities import ChannelContact
from agentgw.domain.contact.repositories import ContactRepository
from agentgw.domain.sync.repositories import SyncRepository


@dataclass
class SyncContactsResult:
    synced_count: int
    next_cursor: dict[str, Any]


class ContactClient(Protocol):
    async def fetch_contacts(self, account_id: str, cursor_payload: dict[str, Any]) -> tuple[list[ChannelContact], dict[str, Any]]:
        raise NotImplementedError


class SyncContactsService:
    def __init__(
        self,
        channel_client: ContactClient,
        cursor_repository: SyncRepository,
        contact_repository: ContactRepository,
    ):
        self._channel_client = channel_client
        self._cursor_repository = cursor_repository
        self._contact_repository = contact_repository

    async def sync_account(self, account_id: str, channel_type: str) -> SyncContactsResult:
        cursor = await self._cursor_repository.get_for_scope(account_id, channel_type, "contacts")
        cursor_payload = cursor.cursor_payload if cursor else {}
        contacts, next_cursor = await self._channel_client.fetch_contacts(account_id, cursor_payload)

        for contact in contacts:
            await self._contact_repository.save(contact)

        await self._cursor_repository.upsert(account_id, channel_type, "contacts", next_cursor)
        return SyncContactsResult(synced_count=len(contacts), next_cursor=next_cursor)
