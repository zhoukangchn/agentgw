from dataclasses import dataclass


@dataclass
class RouteRule:
    channel_type: str
    tenant_id: str
    scene: str | None = None
    bot_id: str | None = None
    agent_endpoint_id: str | None = None
