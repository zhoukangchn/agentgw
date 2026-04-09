from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI

from agentgw.application.services.process_delivery import ProcessDeliveryService
from agentgw.application.services.sync_contacts import SyncContactsService
from agentgw.application.services.sync_messages import SyncMessagesService
from agentgw.infrastructure.channels.feishu.client import FeishuClient
from agentgw.infrastructure.channels.welink.client import WeLinkClient
from agentgw.infrastructure.channels.wecom.client import WeComClient
from agentgw.infrastructure.config.settings import Settings
from agentgw.infrastructure.persistence.base import configure_database
from agentgw.infrastructure.persistence.repositories.contact import SqlAlchemyContactRepository
from agentgw.infrastructure.persistence.repositories.delivery import SqlAlchemyDeliveryRepository
from agentgw.infrastructure.persistence.repositories.message import SqlAlchemyMessageRepository
from agentgw.infrastructure.persistence.repositories.sync import SqlAlchemySyncRepository
from agentgw.infrastructure.providers.agent_ws.provider import WebSocketAgentProvider
from agentgw.infrastructure.workers.jobs import (
    build_process_deliveries_job,
    build_sync_contacts_job,
    build_sync_messages_job,
    parse_targets,
)
from agentgw.infrastructure.workers.dispatcher import DeliveryDispatcher
from agentgw.infrastructure.workers.scheduler import JobDefinition, Scheduler
from agentgw.interfaces.http.controllers.admin_sync import router as admin_sync_router
from agentgw.interfaces.http.controllers.health import router as health_router
from agentgw.interfaces.http.controllers.relay_chat import router as relay_chat_router


@dataclass
class Container:
    settings: Settings
    scheduler: Scheduler
    delivery_dispatcher: DeliveryDispatcher
    sync_message_services: dict[str, SyncMessagesService]
    sync_contact_services: dict[str, SyncContactsService]

    async def trigger_message_sync(self, account_id: str, channel_type: str | None = None) -> None:
        await self._run_sync(account_id, channel_type, self.sync_message_services)

    async def trigger_contact_sync(self, account_id: str, channel_type: str | None = None) -> None:
        await self._run_sync(account_id, channel_type, self.sync_contact_services)

    @staticmethod
    async def _run_sync(
        account_id: str,
        channel_type: str | None,
        services: dict[str, SyncMessagesService] | dict[str, SyncContactsService],
    ) -> None:
        if channel_type is not None:
            service = services.get(channel_type)
            if service is None:
                raise ValueError(f"unsupported channel_type: {channel_type}")
            await service.sync_account(account_id, channel_type)
            return

        for service_channel_type, service in services.items():
            await service.sync_account(account_id, service_channel_type)


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()
    configure_database(settings.database_url)

    sync_repository = SqlAlchemySyncRepository()
    message_repository = SqlAlchemyMessageRepository()
    delivery_repository = SqlAlchemyDeliveryRepository()
    contact_repository = SqlAlchemyContactRepository()

    wecom_client = WeComClient(
        access_token=settings.wecom_access_token,
        audit_proxy=settings.wecom_audit_proxy,
        follow_user_ids=[item.strip() for item in settings.wecom_follow_user_ids.split(",") if item.strip()],
    )
    feishu_client = FeishuClient(
        access_token=settings.feishu_access_token,
        default_chat_id=settings.feishu_default_chat_id,
        department_id=settings.feishu_department_id,
    )
    agent_provider = WebSocketAgentProvider(settings.agent_base_url)
    welink_client = WeLinkClient()
    sync_contact_services = {
        "wecom": SyncContactsService(wecom_client, sync_repository, contact_repository),
        "feishu": SyncContactsService(feishu_client, sync_repository, contact_repository),
    }
    process_delivery_service = ProcessDeliveryService(
        agent_provider=agent_provider,
        message_repository=message_repository,
        delivery_repository=delivery_repository,
        welink_client=welink_client,
    )
    delivery_dispatcher = DeliveryDispatcher(delivery_repository=delivery_repository, process_service=process_delivery_service)
    sync_message_services = {
        "wecom": SyncMessagesService(wecom_client, sync_repository, message_repository, delivery_repository, delivery_dispatcher),
        "feishu": SyncMessagesService(feishu_client, sync_repository, message_repository, delivery_repository, delivery_dispatcher),
    }

    message_targets = parse_targets(settings.message_sync_targets)
    contact_targets = parse_targets(settings.contact_sync_targets)
    scheduler = Scheduler(
        jobs=[
            JobDefinition(
                name="sync-messages",
                interval_seconds=settings.message_sync_interval_seconds,
                callback=build_sync_messages_job(sync_message_services, message_targets),
            ),
            JobDefinition(
                name="sync-contacts",
                interval_seconds=settings.contact_sync_interval_seconds,
                callback=build_sync_contacts_job(sync_contact_services, contact_targets),
            ),
            JobDefinition(
                name="process-deliveries",
                interval_seconds=max(1, settings.message_sync_interval_seconds),
                callback=build_process_deliveries_job(delivery_repository, delivery_dispatcher),
            ),
        ]
    )
    return Container(
        settings=settings,
        scheduler=scheduler,
        delivery_dispatcher=delivery_dispatcher,
        sync_message_services=sync_message_services,
        sync_contact_services=sync_contact_services,
    )


def build_app(container: Container | None = None) -> FastAPI:
    container = container or build_container()
    app = FastAPI(title=container.settings.app_name)
    app.state.container = container
    app.include_router(health_router)
    app.include_router(admin_sync_router)
    app.include_router(relay_chat_router)
    return app
