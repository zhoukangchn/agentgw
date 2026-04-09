from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChannelMode(str, Enum):
    INGRESS_ONLY = "ingress_only"
    ONEWAY = "oneway"
    TWOWAY = "twoway"


class IngressType(str, Enum):
    FEISHU = "feishu"
    WELINK_DM = "welink_dm"


class EgressType(str, Enum):
    NONE = "none"
    WELINK_GROUP = "welink_group"
    WELINK_DM = "welink_dm"


@dataclass(slots=True)
class IngressBinding:
    type: IngressType
    account_id: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentBinding:
    endpoint_id: str


@dataclass(slots=True)
class EgressBinding:
    type: EgressType
    target_id: str | None = None
    use_source_conversation: bool = False
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Channel:
    channel_id: str
    name: str
    ingress: IngressBinding
    agent: AgentBinding
    egress: EgressBinding
    mode: ChannelMode
    enabled: bool = True
