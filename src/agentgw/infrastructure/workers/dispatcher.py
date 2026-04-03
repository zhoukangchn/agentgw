from __future__ import annotations

import asyncio

from agentgw.application.services.process_delivery import ProcessDeliveryService
from agentgw.domain.delivery.repositories import DeliveryRepository


class DeliveryDispatcher:
    def __init__(
        self,
        delivery_repository: DeliveryRepository,
        process_service: ProcessDeliveryService,
    ):
        self._delivery_repository = delivery_repository
        self._process_service = process_service
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._queued: set[str] = set()
        self._inflight: set[str] = set()
        self._worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._run(), name="delivery-dispatcher")

    async def stop(self) -> None:
        if self._worker_task is None:
            return

        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        finally:
            self._worker_task = None
            self._queued.clear()
            self._inflight.clear()

    async def enqueue(self, delivery_id: str) -> None:
        if delivery_id in self._queued or delivery_id in self._inflight:
            return
        self._queued.add(delivery_id)
        await self._queue.put(delivery_id)

    async def _run(self) -> None:
        while True:
            delivery_id = await self._queue.get()
            self._queued.discard(delivery_id)
            self._inflight.add(delivery_id)
            try:
                delivery = await self._delivery_repository.get_by_id(delivery_id)
                await self._process_service.process(delivery)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            finally:
                self._inflight.discard(delivery_id)
                self._queue.task_done()
