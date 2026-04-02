from agentgw.domain.sync.entities import SyncCursor
from agentgw.domain.sync.repositories import SyncRepository
from agentgw.infrastructure.persistence.base import SessionLocal


class SqlAlchemySyncRepository(SyncRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, sync_cursor: SyncCursor) -> SyncCursor:
        raise NotImplementedError("SqlAlchemySyncRepository is not implemented in Task 4")
