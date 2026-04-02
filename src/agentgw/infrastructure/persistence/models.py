from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agentgw.infrastructure.persistence.base import Base


class DeliveryModel(Base):
    __tablename__ = "deliveries"

    delivery_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_endpoint_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    reply_content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class MessageModel(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sender_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sender_is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ContactModel(Base):
    __tablename__ = "contacts"

    contact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    raw_labels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ChannelModel(Base):
    __tablename__ = "channels"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    credentials: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SyncModel(Base):
    __tablename__ = "sync_cursors"

    cursor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cursor_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class RoutingModel(Base):
    __tablename__ = "routing_rules"

    route_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scene: Mapped[str | None] = mapped_column(String(64))
    bot_id: Mapped[str | None] = mapped_column(String(64))
    agent_endpoint_id: Mapped[str | None] = mapped_column(String(64), index=True)


class AgentModel(Base):
    __tablename__ = "agent_endpoints"

    endpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    endpoint_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    auth_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
