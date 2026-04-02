from typing import Protocol

from agentgw.domain.delivery.entities import Delivery


class DeliveryRepository(Protocol):
    async def save(self, delivery: Delivery) -> Delivery:
        raise NotImplementedError

    async def list_pending(self, limit: int = 100) -> list[Delivery]:
        """Return non-terminal deliveries awaiting or in-flight processing.

        Pending deliveries are those whose status is one of:
        RECEIVED, ROUTED, DISPATCHING, DISPATCHED, or REPLYING.
        Terminal statuses SUCCEEDED, FAILED, and DEAD are excluded.
        """
        raise NotImplementedError
