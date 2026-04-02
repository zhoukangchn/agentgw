from sqlalchemy import inspect

from agentgw.infrastructure.persistence.base import Base, engine
from agentgw.infrastructure.persistence.models import ContactModel, DeliveryModel


def test_delivery_table_is_registered() -> None:
    tables = inspect(Base.metadata)
    assert "deliveries" in tables.tables
    assert DeliveryModel.__tablename__ == "deliveries"
    assert "channel_contacts" in tables.tables
    assert ContactModel.__tablename__ == "channel_contacts"
