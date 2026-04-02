from agentgw.domain.channel.entities import ChannelAccount
from agentgw.domain.channel.repositories import ChannelRepository
from agentgw.infrastructure.persistence.base import SessionLocal


class SqlAlchemyChannelRepository(ChannelRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, channel: ChannelAccount) -> ChannelAccount:
        raise NotImplementedError("SqlAlchemyChannelRepository is not implemented in Task 4")
