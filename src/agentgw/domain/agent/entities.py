from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentTransportType(str, Enum):
    WS_RPC = "ws_rpc"
    SDK_SESSION = "sdk_session"


@dataclass(slots=True)
class AgentEndpoint:
    endpoint_id: str
    name: str
    transport: AgentTransportType
    url: str
    timeout_seconds: int = 30
    sdk_module: str | None = None
    sdk_client_class: str = "RelayClient"
    sdk_event_enum: str = "EventType"
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResult:
    endpoint_id: str
    final_text: str
    raw_events: list[dict[str, Any]] = field(default_factory=list)
