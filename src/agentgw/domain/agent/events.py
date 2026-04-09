from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentEventType(str, Enum):
    AGENT_CALL = "agent_call"
    AGENT_TEXT = "agent_text"
    TOOL_EXECUTION = "tool_execution"
    DONE = "done"
    ERROR = "error"
    DEBUG = "debug"


@dataclass(slots=True)
class AgentEvent:
    session_id: str | None
    event_type: AgentEventType
    payload: dict[str, Any] = field(default_factory=dict)
    raw_payload: Any = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
