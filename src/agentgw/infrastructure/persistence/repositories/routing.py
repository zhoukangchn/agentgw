from agentgw.domain.routing.entities import RouteRule
from agentgw.domain.routing.repositories import RoutingRepository
from agentgw.infrastructure.persistence.base import SessionLocal


class SqlAlchemyRoutingRepository(RoutingRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, route_rule: RouteRule) -> RouteRule:
        raise NotImplementedError("SqlAlchemyRoutingRepository is not implemented in Task 4")
