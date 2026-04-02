from agentgw.domain.message.entities import ChannelMessage
from agentgw.domain.message.repositories import MessageRepository
from agentgw.infrastructure.persistence.base import SessionLocal
from agentgw.infrastructure.persistence.models import MessageModel


class SqlAlchemyMessageRepository(MessageRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, message: ChannelMessage) -> ChannelMessage:
        with self._session_factory() as session:
            row = session.get(MessageModel, message.message_id)
            if row is None:
                row = MessageModel(message_id=message.message_id)

            row.channel_type = message.channel_type
            row.account_id = message.account_id
            row.conversation_id = message.conversation_id
            row.sender_id = message.sender_id
            row.sender_is_internal = message.sender_is_internal
            row.content = message.content
            row.sent_at = message.sent_at
            row.raw_payload = message.raw_payload
            session.add(row)
            session.commit()
            return message
