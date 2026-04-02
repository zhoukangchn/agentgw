from typing import Any

from agentgw.domain.sync.entities import SyncCursor
from agentgw.domain.sync.repositories import SyncRepository
from agentgw.infrastructure.persistence.base import SessionLocal


class SqlAlchemySyncRepository(SyncRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def get_for_scope(self, account_id: str, scope: str) -> SyncCursor | None:
        raise NotImplementedError("SqlAlchemySyncRepository is not implemented in Task 4")

    async def upsert(self, account_id: str, scope: str, payload: dict[str, Any]) -> SyncCursor:
        raise NotImplementedError("SqlAlchemySyncRepository is not implemented in Task 4")
