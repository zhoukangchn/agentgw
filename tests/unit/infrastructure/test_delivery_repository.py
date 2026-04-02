import pytest

from agentgw.domain.delivery.entities import Delivery
from agentgw.infrastructure.persistence.repositories.delivery import SqlAlchemyDeliveryRepository


@pytest.mark.anyio
async def test_delivery_repository_persists_delivery() -> None:
    repo = SqlAlchemyDeliveryRepository()

    saved = await repo.save(Delivery.create("msg-1"))

    assert saved.delivery_id is not None
    pending = await repo.list_pending()
    assert [delivery.message_id for delivery in pending] == ["msg-1"]
