import pytest

from agentgw.infrastructure.persistence.repositories.sync import SqlAlchemySyncRepository


@pytest.mark.anyio
async def test_sync_repository_upsert_and_get_for_scope_round_trips_cursor() -> None:
    repo = SqlAlchemySyncRepository()

    saved = await repo.upsert("acc-1", "messages", {"seq": 10})
    loaded = await repo.get_for_scope("acc-1", "messages")

    assert saved.cursor_id == "acc-1:messages"
    assert loaded is not None
    assert loaded.cursor_id == "acc-1:messages"
    assert loaded.account_id == "acc-1"
    assert loaded.scope == "messages"
    assert loaded.cursor_payload == {"seq": 10}
