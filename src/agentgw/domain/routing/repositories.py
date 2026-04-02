from typing import Protocol

from agentgw.domain.routing.entities import RouteRule


class RoutingRepository(Protocol):
    async def save(self, route_rule: RouteRule) -> RouteRule:
        raise NotImplementedError
