from agentgw.domain.sync.entities import SyncCursor
from agentgw.domain.sync.repositories import SyncRepository
from agentgw.infrastructure.persistence.base import SessionLocal
from agentgw.infrastructure.persistence.models import SyncModel


class SqlAlchemySyncRepository(SyncRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, sync_cursor: SyncCursor) -> SyncCursor:
        with self._session_factory() as session:
            row = session.get(SyncModel, sync_cursor.cursor_id)
            if row is None:
                row = SyncModel(cursor_id=sync_cursor.cursor_id)

            row.channel_type = sync_cursor.channel_type
            row.account_id = sync_cursor.account_id
            row.scope = sync_cursor.scope
            row.cursor_payload = sync_cursor.cursor_payload
            row.updated_at = sync_cursor.updated_at
            session.add(row)
            session.commit()
            return sync_cursor
