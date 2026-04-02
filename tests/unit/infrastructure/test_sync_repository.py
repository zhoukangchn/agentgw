import pytest

from agentgw.infrastructure.persistence.repositories.sync import SqlAlchemySyncRepository


@pytest.mark.anyio
async def test_sync_repository_upsert_and_get_for_scope_round_trips_cursor() -> None:
    repo = SqlAlchemySyncRepository()

    saved = await repo.upsert("acc-1", "wecom", "messages", {"seq": 10})
    loaded = await repo.get_for_scope("acc-1", "wecom", "messages")

    assert saved.cursor_id == "wecom:acc-1:messages"
    assert loaded is not None
    assert loaded.cursor_id == "wecom:acc-1:messages"
    assert loaded.account_id == "acc-1"
    assert loaded.channel_type == "wecom"
    assert loaded.scope == "messages"
    assert loaded.cursor_payload == {"seq": 10}


@pytest.mark.anyio
async def test_sync_repository_separates_cursors_by_channel_type() -> None:
    repo = SqlAlchemySyncRepository()

    await repo.upsert("acc-1", "wecom", "messages", {"seq": 10})
    await repo.upsert("acc-1", "feishu", "messages", {"cursor": "abc"})

    wecom_cursor = await repo.get_for_scope("acc-1", "wecom", "messages")
    feishu_cursor = await repo.get_for_scope("acc-1", "feishu", "messages")

    assert wecom_cursor is not None
    assert feishu_cursor is not None
    assert wecom_cursor.cursor_payload == {"seq": 10}
    assert feishu_cursor.cursor_payload == {"cursor": "abc"}
