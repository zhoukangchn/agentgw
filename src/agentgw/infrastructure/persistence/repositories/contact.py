from datetime import UTC, datetime

from agentgw.domain.contact.entities import ChannelContact
from agentgw.domain.contact.repositories import ContactRepository
from agentgw.infrastructure.persistence.base import SessionLocal, initialize_schema
from agentgw.infrastructure.persistence.models import ContactModel


class SqlAlchemyContactRepository(ContactRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        initialize_schema()

    async def save(self, contact: ChannelContact) -> ChannelContact:
        with self._session_factory() as session:
            contact_key = self._contact_key(contact)
            row = session.get(ContactModel, contact_key)
            if row is None:
                row = ContactModel(contact_key=contact_key, contact_id=contact.contact_id)

            row.contact_id = contact.contact_id
            row.channel_type = contact.channel_type
            row.account_id = contact.account_id
            row.display_name = contact.display_name
            row.is_internal = contact.is_internal
            row.raw_labels = list(contact.raw_labels)
            row.updated_at = datetime.now(UTC)
            session.add(row)
            session.commit()
            return self._to_entity(row)

    @staticmethod
    def _contact_key(contact: ChannelContact) -> str:
        return f"{contact.channel_type}:{contact.account_id}:{contact.contact_id}"

    @staticmethod
    def _to_entity(row: ContactModel) -> ChannelContact:
        return ChannelContact(
            contact_id=row.contact_id,
            channel_type=row.channel_type,
            account_id=row.account_id,
            display_name=row.display_name,
            is_internal=row.is_internal,
            raw_labels=list(row.raw_labels),
            updated_at=row.updated_at,
        )
