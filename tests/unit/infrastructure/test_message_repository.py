import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from agentgw.domain.message.entities import ChannelMessage
from agentgw.infrastructure.persistence.models import MessageModel
from agentgw.infrastructure.persistence.repositories.message import SqlAlchemyMessageRepository


@pytest.mark.anyio
async def test_message_repository_save_persists_and_reloads_message(
    sqlite_session_factory: sessionmaker,
) -> None:
    repo = SqlAlchemyMessageRepository(session_factory=sqlite_session_factory)
    message = ChannelMessage(
        message_id="msg-1",
        channel_type="wecom",
        account_id="acc-1",
        conversation_id="conv-1",
        sender_id="user-1",
        sender_is_internal=False,
        content="hello",
        sent_at=__import__("datetime").datetime.now(),
        raw_payload={"seq": 10},
    )

    saved = await repo.save(message)

    assert saved.message_id == "msg-1"

    with sqlite_session_factory() as session:
        row = session.execute(
            select(MessageModel).where(
                MessageModel.message_id == "msg-1",
                MessageModel.channel_type == "wecom",
                MessageModel.account_id == "acc-1",
            )
        ).scalars().one()

    assert row.content == "hello"
    assert row.raw_payload == {"seq": 10}
