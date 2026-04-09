from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True)
class Conversation:
    conversation_id: str
    channel_id: str
    source_conversation_id: str
    source_user_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, conversation_id: str, channel_id: str, source_conversation_id: str, source_user_id: str) -> "Conversation":
        now = datetime.now(UTC)
        return cls(
            conversation_id=conversation_id,
            channel_id=channel_id,
            source_conversation_id=source_conversation_id,
            source_user_id=source_user_id,
            created_at=now,
            updated_at=now,
        )
