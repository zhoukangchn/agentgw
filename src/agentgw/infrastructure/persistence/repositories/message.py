from datetime import UTC, datetime

from agentgw.domain.message.entities import ChannelMessage
from agentgw.domain.message.repositories import MessageRepository
from agentgw.infrastructure.persistence.base import SessionLocal, initialize_schema
from agentgw.infrastructure.persistence.models import MessageModel


class SqlAlchemyMessageRepository(MessageRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        initialize_schema()

    async def save(self, message: ChannelMessage) -> ChannelMessage:
        with self._session_factory() as session:
            message_key = self._message_key(message)
            row = session.get(MessageModel, message_key)
            if row is None:
                row = MessageModel(message_key=message_key, message_id=message.message_id)
            row.message_id = message.message_id
            row.channel_type = message.channel_type
            row.account_id = message.account_id
            row.conversation_id = message.conversation_id
            row.sender_id = message.sender_id
            row.sender_is_internal = message.sender_is_internal
            row.content = message.content
            row.sent_at = message.sent_at
            row.raw_payload = message.raw_payload
            row.updated_at = datetime.now(UTC)
            session.add(row)
            session.commit()
            return self._to_entity(row)

    @staticmethod
    def _message_key(message: ChannelMessage) -> str:
        return f"{message.channel_type}:{message.account_id}:{message.message_id}"

    async def get_by_message_id(self, message_id: str) -> ChannelMessage:
        with self._session_factory() as session:
            row = (
                session.query(MessageModel)
                .filter(MessageModel.message_id == message_id)
                .order_by(MessageModel.updated_at.desc())
                .first()
            )
            if row is None:
                raise LookupError(f"missing message: {message_id}")
            return self._to_entity(row)

    @staticmethod
    def _to_entity(row: MessageModel) -> ChannelMessage:
        return ChannelMessage(
            message_id=row.message_id,
            channel_type=row.channel_type,
            account_id=row.account_id,
            conversation_id=row.conversation_id,
            sender_id=row.sender_id,
            sender_is_internal=row.sender_is_internal,
            content=row.content,
            sent_at=row.sent_at,
            raw_payload=dict(row.raw_payload),
        )
