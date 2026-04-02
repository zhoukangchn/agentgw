from agentgw.domain.message.entities import ChannelMessage
from agentgw.domain.message.repositories import MessageRepository
from agentgw.infrastructure.persistence.base import SessionLocal


class SqlAlchemyMessageRepository(MessageRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, message: ChannelMessage) -> ChannelMessage:
        with self._session_factory():
            return message
