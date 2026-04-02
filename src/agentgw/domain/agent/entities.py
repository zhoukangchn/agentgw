from dataclasses import dataclass
from typing import Any


@dataclass
class AgentEndpoint:
    endpoint_id: str
    endpoint_type: str
    base_url: str
    auth_config: dict[str, Any]
    timeout_seconds: int = 30
