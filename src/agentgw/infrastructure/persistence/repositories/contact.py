from agentgw.domain.contact.entities import ChannelContact
from agentgw.domain.contact.repositories import ContactRepository
from agentgw.infrastructure.persistence.base import SessionLocal


class SqlAlchemyContactRepository(ContactRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, contact: ChannelContact) -> ChannelContact:
        raise NotImplementedError("SqlAlchemyContactRepository is not implemented in Task 4")
