from agentgw.domain.contact.entities import ChannelContact
from agentgw.domain.contact.repositories import ContactRepository
from agentgw.infrastructure.persistence.base import SessionLocal
from agentgw.infrastructure.persistence.models import ContactModel


class SqlAlchemyContactRepository(ContactRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, contact: ChannelContact) -> ChannelContact:
        with self._session_factory() as session:
            row = session.get(ContactModel, contact.contact_id)
            if row is None:
                row = ContactModel(contact_id=contact.contact_id)

            row.channel_type = contact.channel_type
            row.account_id = contact.account_id
            row.display_name = contact.display_name
            row.is_internal = contact.is_internal
            row.raw_labels = contact.raw_labels
            row.updated_at = contact.updated_at
            session.add(row)
            session.commit()
            return contact
