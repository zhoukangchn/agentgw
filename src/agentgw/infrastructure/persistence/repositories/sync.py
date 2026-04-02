from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from agentgw.domain.sync.entities import SyncCursor
from agentgw.domain.sync.repositories import SyncRepository
from agentgw.infrastructure.persistence.base import SessionLocal
from agentgw.infrastructure.persistence.models import SyncCursorModel


class SqlAlchemySyncRepository(SyncRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        from agentgw.infrastructure.persistence.base import initialize_schema

        initialize_schema()

    async def get_for_scope(self, account_id: str, scope: str) -> SyncCursor | None:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(SyncCursorModel).where(
                        SyncCursorModel.account_id == account_id,
                        SyncCursorModel.scope == scope,
                    )
                )
                .scalars()
                .one_or_none()
            )
            return self._to_entity(row) if row is not None else None

    async def upsert(self, account_id: str, scope: str, payload: dict[str, Any]) -> SyncCursor:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(SyncCursorModel).where(
                        SyncCursorModel.account_id == account_id,
                        SyncCursorModel.scope == scope,
                    )
                )
                .scalars()
                .one_or_none()
            )
            if row is None:
                row = SyncCursorModel(
                    cursor_id=self._cursor_id(account_id, scope),
                    channel_type="unknown",
                    account_id=account_id,
                    scope=scope,
                )
            row.cursor_payload = payload
            row.updated_at = datetime.now(UTC)
            session.add(row)
            session.commit()
            return self._to_entity(row)

    @staticmethod
    def _cursor_id(account_id: str, scope: str) -> str:
        return f"{account_id}:{scope}"

    @staticmethod
    def _to_entity(row: SyncCursorModel) -> SyncCursor:
        return SyncCursor(
            cursor_id=row.cursor_id,
            channel_type=row.channel_type,
            account_id=row.account_id,
            scope=row.scope,
            cursor_payload=dict(row.cursor_payload),
            updated_at=row.updated_at,
        )
