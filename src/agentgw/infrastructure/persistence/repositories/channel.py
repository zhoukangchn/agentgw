from agentgw.domain.channel.entities import ChannelAccount
from agentgw.domain.channel.repositories import ChannelRepository
from agentgw.infrastructure.persistence.base import SessionLocal
from agentgw.infrastructure.persistence.models import ChannelModel


class SqlAlchemyChannelRepository(ChannelRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, channel: ChannelAccount) -> ChannelAccount:
        with self._session_factory() as session:
            row = session.get(ChannelModel, channel.account_id)
            if row is None:
                row = ChannelModel(account_id=channel.account_id)

            row.channel_type = channel.channel_type
            row.tenant_id = channel.tenant_id
            row.credentials = channel.credentials
            row.enabled = channel.enabled
            session.add(row)
            session.commit()
            return channel
