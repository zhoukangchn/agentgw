from typing import Protocol

from agentgw.domain.message.entities import ChannelMessage


class MessageRepository(Protocol):
    async def save(self, message: ChannelMessage) -> ChannelMessage:
        raise NotImplementedError
