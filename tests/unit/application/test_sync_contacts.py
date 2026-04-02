from typing import Any

import pytest

from agentgw.application.services.sync_contacts import SyncContactsService
from agentgw.domain.contact.entities import ChannelContact
from agentgw.domain.sync.entities import SyncCursor


class FakeChannelClient:
    async def fetch_contacts(
        self,
        account_id: str,
        cursor_payload: dict[str, Any],
    ) -> tuple[list[ChannelContact], dict[str, Any]]:
        return (
            [
                ChannelContact(
                    contact_id="contact-1",
                    channel_type="wecom",
                    account_id=account_id,
                    display_name="Alice",
                    is_internal=False,
                    raw_labels=["vip"],
                )
            ],
            {"next_cursor": "cursor-2"},
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
            cursor_payload={"next_cursor": "cursor-1"},
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


class FakeContactRepository:
    def __init__(self):
        self.saved_contacts: list[ChannelContact] = []

    async def save(self, contact: ChannelContact) -> ChannelContact:
        self.saved_contacts.append(contact)
        return contact


@pytest.mark.asyncio
async def test_sync_contacts_persists_contacts_and_updates_cursor() -> None:
    cursor_repository = FakeCursorRepository()
    contact_repository = FakeContactRepository()
    service = SyncContactsService(
        channel_client=FakeChannelClient(),
        cursor_repository=cursor_repository,
        contact_repository=contact_repository,
    )

    result = await service.sync_account("acc-1", "wecom")

    assert result.synced_count == 1
    assert result.next_cursor == {"next_cursor": "cursor-2"}
    assert cursor_repository.saved_cursor is not None
    assert cursor_repository.saved_cursor.cursor_payload == {"next_cursor": "cursor-2"}
    assert len(contact_repository.saved_contacts) == 1
