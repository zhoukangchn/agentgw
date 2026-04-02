from typing import Any, Protocol

from agentgw.domain.sync.entities import SyncCursor


class SyncRepository(Protocol):
    async def get_for_scope(self, account_id: str, channel_type: str, scope: str) -> SyncCursor | None:
        raise NotImplementedError

    async def upsert(self, account_id: str, channel_type: str, scope: str, payload: dict[str, Any]) -> SyncCursor:
        raise NotImplementedError
