from typing import Protocol

from agentgw.domain.channel.entities import ChannelAccount


class ChannelRepository(Protocol):
    async def save(self, channel: ChannelAccount) -> ChannelAccount:
        raise NotImplementedError
