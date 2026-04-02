from collections.abc import Iterator

import pytest
from sqlalchemy import delete

from agentgw.infrastructure.persistence.base import SessionLocal, initialize_schema
from agentgw.infrastructure.persistence.models import DeliveryModel, MessageModel, SyncCursorModel


@pytest.fixture(autouse=True)
def clean_persistence_state() -> Iterator[None]:
    initialize_schema()
    with SessionLocal() as session:
        session.execute(delete(MessageModel))
        session.execute(delete(SyncCursorModel))
        session.execute(delete(DeliveryModel))
        session.commit()
    yield
