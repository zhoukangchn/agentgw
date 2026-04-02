from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from agentgw.application.services.process_delivery import ProcessDeliveryService
from agentgw.application.services.sync_contacts import SyncContactsService
from agentgw.application.services.sync_messages import SyncMessagesService
from agentgw.domain.delivery.repositories import DeliveryRepository


@dataclass(frozen=True)
class SyncTarget:
    channel_type: str
    account_id: str


def parse_targets(raw_targets: str) -> list[SyncTarget]:
    targets: list[SyncTarget] = []
    for item in raw_targets.split(","):
        value = item.strip()
        if not value:
            continue
        channel_type, _, account_id = value.partition(":")
        if channel_type and account_id:
            targets.append(SyncTarget(channel_type=channel_type, account_id=account_id))
    return targets


def build_sync_messages_job(
    sync_services: dict[str, SyncMessagesService],
    targets: Sequence[SyncTarget],
):
    async def job() -> None:
        for target in targets:
            service = sync_services.get(target.channel_type)
            if service is not None:
                await service.sync_account(target.account_id, target.channel_type)

    return job


def build_sync_contacts_job(
    sync_services: dict[str, SyncContactsService],
    targets: Sequence[SyncTarget],
):
    async def job() -> None:
        for target in targets:
            service = sync_services.get(target.channel_type)
            if service is not None:
                await service.sync_account(target.account_id, target.channel_type)

    return job


def build_process_deliveries_job(
    delivery_repository: DeliveryRepository,
    process_service: ProcessDeliveryService,
):
    async def job() -> None:
        deliveries = await delivery_repository.list_pending()
        for delivery in deliveries:
            await process_service.process(delivery)

    return job
