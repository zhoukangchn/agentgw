from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI

from agentgw.adapters.agent.sdk_session import SdkSessionTransport
from agentgw.adapters.agent.ws_rpc import WsRpcTransport
from agentgw.adapters.egress.dispatcher import EgressDispatcher
from agentgw.adapters.egress.welink import WeLinkHttpService, WeLinkMockService
from agentgw.application.orchestration.runtime import RuntimeOrchestrator
from agentgw.application.routing.channel_router import ChannelRouter
from agentgw.domain.agent.entities import AgentEndpoint, AgentTransportType
from agentgw.domain.channel.entities import AgentBinding, Channel, ChannelMode, EgressBinding, EgressType, IngressBinding, IngressType
from agentgw.infrastructure.config.settings import Settings
from agentgw.infrastructure.persistence.base import configure_database
from agentgw.infrastructure.persistence.repositories import AgentEndpointRepository, ChannelRepository, ConversationRepository, MessageRepository
from agentgw.interfaces.http.routes import router


class TransportRegistry:
    def __init__(self, transports: dict[str, object]) -> None:
        self._transports = transports

    def get(self, transport_type: str):
        try:
            return self._transports[transport_type]
        except KeyError as exc:
            raise LookupError(f"missing transport: {transport_type}") from exc


@dataclass
class Container:
    settings: Settings
    channel_repository: ChannelRepository
    endpoint_repository: AgentEndpointRepository
    conversation_repository: ConversationRepository
    message_repository: MessageRepository
    welink_service: object
    runtime: RuntimeOrchestrator


def build_welink_service(settings: Settings):
    if settings.welink_adapter_mode == "mock":
        return WeLinkMockService()

    if settings.welink_adapter_mode == "http":
        if not settings.welink_base_url or not settings.welink_access_token:
            raise RuntimeError("welink_base_url and welink_access_token are required when welink_adapter_mode=http")
        return WeLinkHttpService(
            base_url=settings.welink_base_url,
            access_token=settings.welink_access_token,
            group_message_path=settings.welink_group_message_path,
            private_message_path=settings.welink_private_message_path,
        )

    raise RuntimeError(f"unsupported welink_adapter_mode: {settings.welink_adapter_mode}")


def seed_defaults(channel_repository: ChannelRepository, endpoint_repository: AgentEndpointRepository, settings: Settings) -> None:
    endpoint_repository.upsert(
        AgentEndpoint(
            endpoint_id="agent_ws_default",
            name="Default WS agent",
            transport=AgentTransportType.WS_RPC,
            url=settings.ws_agent_url,
        )
    )
    endpoint_repository.upsert(
        AgentEndpoint(
            endpoint_id="agent_sdk_default",
            name="Default SDK agent",
            transport=AgentTransportType.SDK_SESSION,
            url=settings.sdk_agent_url,
            sdk_module=settings.sdk_module,
        )
    )

    channel_repository.upsert(
        Channel(
            channel_id="feishu_ingress",
            name="飞书只采集",
            ingress=IngressBinding(type=IngressType.FEISHU, account_id="acc-feishu-default"),
            agent=AgentBinding(endpoint_id="agent_ws_default"),
            egress=EgressBinding(type=EgressType.NONE),
            mode=ChannelMode.INGRESS_ONLY,
        )
    )
    channel_repository.upsert(
        Channel(
            channel_id="feishu_to_welink_group",
            name="飞书转 WeLink 群",
            ingress=IngressBinding(type=IngressType.FEISHU, account_id="acc-feishu-default"),
            agent=AgentBinding(endpoint_id="agent_ws_default"),
            egress=EgressBinding(type=EgressType.WELINK_GROUP, target_id="welink-group-demo"),
            mode=ChannelMode.ONEWAY,
        )
    )
    channel_repository.upsert(
        Channel(
            channel_id="welink_dm_twoway",
            name="WeLink 私聊双向",
            ingress=IngressBinding(type=IngressType.WELINK_DM, account_id="acc-welink-default"),
            agent=AgentBinding(endpoint_id="agent_sdk_default"),
            egress=EgressBinding(type=EgressType.WELINK_DM, use_source_conversation=True),
            mode=ChannelMode.TWOWAY,
        )
    )


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()
    configure_database(settings.database_url)
    channel_repository = ChannelRepository()
    endpoint_repository = AgentEndpointRepository()
    conversation_repository = ConversationRepository()
    message_repository = MessageRepository()
    seed_defaults(channel_repository, endpoint_repository, settings)
    welink_service = build_welink_service(settings)
    transport_registry = TransportRegistry(
        {
            AgentTransportType.WS_RPC.value: WsRpcTransport(),
            AgentTransportType.SDK_SESSION.value: SdkSessionTransport(),
        }
    )
    runtime = RuntimeOrchestrator(
        channel_router=ChannelRouter(channel_repository),
        endpoint_repository=endpoint_repository,
        transport_registry=transport_registry,
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        egress_dispatcher=EgressDispatcher(welink_service),
    )
    return Container(
        settings=settings,
        channel_repository=channel_repository,
        endpoint_repository=endpoint_repository,
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        welink_service=welink_service,
        runtime=runtime,
    )


def build_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(title=(container.settings.app_name if container else Settings().app_name))
    app.state.container = container or build_container()
    app.include_router(router)
    return app
