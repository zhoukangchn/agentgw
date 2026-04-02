from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChannelAccount:
    account_id: str
    channel_type: str
    tenant_id: str
    credentials: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
