from typing import Protocol

from agentgw.domain.contact.entities import ChannelContact


class ContactRepository(Protocol):
    async def save(self, contact: ChannelContact) -> ChannelContact:
        raise NotImplementedError
