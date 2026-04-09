from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from agentgw.domain.agent.entities import AgentEndpoint, AgentTransportType
from agentgw.domain.channel.entities import AgentBinding, Channel, ChannelMode, EgressBinding, EgressType, IngressBinding, IngressType
from agentgw.domain.conversation.entities import Conversation
from agentgw.domain.message.entities import Message, MessageDirection
from agentgw.infrastructure.persistence.base import SessionLocal, initialize_schema
from agentgw.infrastructure.persistence.models import AgentEndpointModel, ChannelModel, ConversationModel, MessageModel


class ChannelRepository:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        initialize_schema()

    def get(self, channel_id: str) -> Channel:
        with self._session_factory() as session:
            row = session.get(ChannelModel, channel_id)
            if row is None:
                raise LookupError(f"missing channel: {channel_id}")
            return Channel(
                channel_id=row.channel_id,
                name=row.name,
                ingress=IngressBinding(type=IngressType(row.ingress_type), account_id=row.ingress_account_id),
                agent=AgentBinding(endpoint_id=row.agent_endpoint_id),
                egress=EgressBinding(
                    type=EgressType(row.egress_type),
                    target_id=row.egress_target_id,
                    use_source_conversation=row.use_source_conversation,
                    config=dict(row.config_json or {}),
                ),
                mode=ChannelMode(row.mode),
                enabled=row.enabled,
            )

    def list(self) -> list[Channel]:
        with self._session_factory() as session:
            rows = session.execute(select(ChannelModel).order_by(ChannelModel.channel_id)).scalars().all()
            return [
                Channel(
                    channel_id=row.channel_id,
                    name=row.name,
                    ingress=IngressBinding(type=IngressType(row.ingress_type), account_id=row.ingress_account_id),
                    agent=AgentBinding(endpoint_id=row.agent_endpoint_id),
                    egress=EgressBinding(
                        type=EgressType(row.egress_type),
                        target_id=row.egress_target_id,
                        use_source_conversation=row.use_source_conversation,
                        config=dict(row.config_json or {}),
                    ),
                    mode=ChannelMode(row.mode),
                    enabled=row.enabled,
                )
                for row in rows
            ]

    def upsert(self, channel: Channel) -> None:
        with self._session_factory() as session:
            row = session.get(ChannelModel, channel.channel_id) or ChannelModel(channel_id=channel.channel_id)
            row.name = channel.name
            row.ingress_type = channel.ingress.type.value
            row.ingress_account_id = channel.ingress.account_id
            row.agent_endpoint_id = channel.agent.endpoint_id
            row.egress_type = channel.egress.type.value
            row.egress_target_id = channel.egress.target_id
            row.use_source_conversation = channel.egress.use_source_conversation
            row.mode = channel.mode.value
            row.enabled = channel.enabled
            row.config_json = {}
            session.add(row)
            session.commit()


class AgentEndpointRepository:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        initialize_schema()

    def get(self, endpoint_id: str) -> AgentEndpoint:
        with self._session_factory() as session:
            row = session.get(AgentEndpointModel, endpoint_id)
            if row is None:
                raise LookupError(f"missing endpoint: {endpoint_id}")
            if not row.enabled:
                raise LookupError(f"endpoint disabled: {endpoint_id}")
            return AgentEndpoint(
                endpoint_id=row.endpoint_id,
                name=row.name,
                transport=AgentTransportType(row.transport),
                url=row.url,
                timeout_seconds=row.timeout_seconds,
                sdk_module=row.sdk_module,
                sdk_client_class=row.sdk_client_class or "RelayClient",
                sdk_event_enum=row.sdk_event_enum or "EventType",
                enabled=row.enabled,
                config=dict(row.config_json or {}),
            )

    def list(self) -> list[AgentEndpoint]:
        with self._session_factory() as session:
            rows = session.execute(select(AgentEndpointModel).order_by(AgentEndpointModel.endpoint_id)).scalars().all()
            return [
                AgentEndpoint(
                    endpoint_id=row.endpoint_id,
                    name=row.name,
                    transport=AgentTransportType(row.transport),
                    url=row.url,
                    timeout_seconds=row.timeout_seconds,
                    sdk_module=row.sdk_module,
                    sdk_client_class=row.sdk_client_class or "RelayClient",
                    sdk_event_enum=row.sdk_event_enum or "EventType",
                    enabled=row.enabled,
                    config=dict(row.config_json or {}),
                )
                for row in rows
            ]

    def upsert(self, endpoint: AgentEndpoint) -> None:
        with self._session_factory() as session:
            row = session.get(AgentEndpointModel, endpoint.endpoint_id) or AgentEndpointModel(endpoint_id=endpoint.endpoint_id)
            row.name = endpoint.name
            row.transport = endpoint.transport.value
            row.url = endpoint.url
            row.timeout_seconds = endpoint.timeout_seconds
            row.sdk_module = endpoint.sdk_module
            row.sdk_client_class = endpoint.sdk_client_class
            row.sdk_event_enum = endpoint.sdk_event_enum
            row.enabled = endpoint.enabled
            row.config_json = dict(endpoint.config)
            session.add(row)
            session.commit()


class ConversationRepository:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        initialize_schema()

    def get_or_create(self, *, channel_id: str, source_conversation_id: str, source_user_id: str) -> Conversation:
        with self._session_factory() as session:
            row = session.execute(
                select(ConversationModel).where(
                    ConversationModel.channel_id == channel_id,
                    ConversationModel.source_conversation_id == source_conversation_id,
                )
            ).scalar_one_or_none()
            if row is not None:
                row.updated_at = datetime.now(UTC)
                session.add(row)
                session.commit()
                return Conversation(
                    conversation_id=row.conversation_id,
                    channel_id=row.channel_id,
                    source_conversation_id=row.source_conversation_id,
                    source_user_id=row.source_user_id,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )

            conversation = Conversation.create(
                conversation_id=f"conv_{uuid4().hex}",
                channel_id=channel_id,
                source_conversation_id=source_conversation_id,
                source_user_id=source_user_id,
            )
            session.add(
                ConversationModel(
                    conversation_id=conversation.conversation_id,
                    channel_id=conversation.channel_id,
                    source_conversation_id=conversation.source_conversation_id,
                    source_user_id=conversation.source_user_id,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                )
            )
            session.commit()
            return conversation


class MessageRepository:
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory
        initialize_schema()

    def add(self, message: Message) -> None:
        with self._session_factory() as session:
            session.add(
                MessageModel(
                    message_id=message.message_id,
                    channel_id=message.channel_id,
                    conversation_id=message.conversation_id,
                    sender_id=message.sender_id,
                    direction=message.direction.value,
                    content=message.content,
                    raw_payload_json=message.raw_payload,
                    created_at=message.created_at,
                )
            )
            session.commit()

    def list(self) -> list[Message]:
        with self._session_factory() as session:
            rows = session.execute(select(MessageModel).order_by(MessageModel.created_at.asc())).scalars().all()
            return [
                Message(
                    message_id=row.message_id,
                    channel_id=row.channel_id,
                    conversation_id=row.conversation_id,
                    sender_id=row.sender_id,
                    direction=MessageDirection(row.direction),
                    content=row.content,
                    raw_payload=row.raw_payload_json,
                    created_at=row.created_at,
                )
                for row in rows
            ]
