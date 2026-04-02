from typing import Protocol

from agentgw.domain.sync.entities import SyncCursor


class SyncRepository(Protocol):
    async def save(self, sync_cursor: SyncCursor) -> SyncCursor:
        raise NotImplementedError
