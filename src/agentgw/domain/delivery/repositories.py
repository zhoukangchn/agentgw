from typing import Protocol

from agentgw.domain.delivery.entities import Delivery


class DeliveryRepository(Protocol):
    async def save(self, delivery: Delivery) -> Delivery:
        raise NotImplementedError

    async def list_pending(self, limit: int = 100) -> list[Delivery]:
        raise NotImplementedError
