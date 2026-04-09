from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    AGENT = "agent"
    EGRESS = "egress"


@dataclass(slots=True)
class Message:
    message_id: str
    channel_id: str
    conversation_id: str
    sender_id: str
    direction: MessageDirection
    content: str
    raw_payload: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
