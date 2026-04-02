import pytest
from sqlalchemy.orm import sessionmaker

from agentgw.domain.delivery.entities import Delivery
from agentgw.infrastructure.persistence.repositories.delivery import SqlAlchemyDeliveryRepository


@pytest.mark.anyio
async def test_delivery_repository_persists_delivery(
    sqlite_session_factory: sessionmaker,
) -> None:
    repo = SqlAlchemyDeliveryRepository(session_factory=sqlite_session_factory)

    saved = await repo.save(Delivery.create("msg-1"))

    assert saved.delivery_id is not None
    pending = await repo.list_pending()
    assert [delivery.message_id for delivery in pending] == ["msg-1"]
