import asyncio

import pytest

from agentgw.domain.delivery.entities import Delivery
from agentgw.infrastructure.workers.dispatcher import DeliveryDispatcher


class FakeDeliveryRepository:
    def __init__(self, delivery: Delivery):
        self._delivery = delivery
        self.lookups: list[str] = []

    async def get_by_id(self, delivery_id: str) -> Delivery:
        self.lookups.append(delivery_id)
        return self._delivery


class FakeProcessDeliveryService:
    def __init__(self):
        self.processed_ids: list[str] = []
        self.event = asyncio.Event()

    async def process(self, delivery: Delivery) -> Delivery:
        self.processed_ids.append(delivery.delivery_id or "")
        self.event.set()
        return delivery


@pytest.mark.asyncio
async def test_dispatcher_processes_enqueued_delivery() -> None:
    delivery = Delivery.create(message_id="msg-1")
    delivery.delivery_id = "delivery-1"
    repository = FakeDeliveryRepository(delivery)
    process_service = FakeProcessDeliveryService()
    dispatcher = DeliveryDispatcher(delivery_repository=repository, process_service=process_service)

    await dispatcher.start()
    await dispatcher.enqueue("delivery-1")
    await asyncio.wait_for(process_service.event.wait(), timeout=1)
    await dispatcher.stop()

    assert repository.lookups == ["delivery-1"]
    assert process_service.processed_ids == ["delivery-1"]
