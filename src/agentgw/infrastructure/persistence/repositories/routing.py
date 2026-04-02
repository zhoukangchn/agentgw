from uuid import uuid4

from agentgw.domain.routing.entities import RouteRule
from agentgw.domain.routing.repositories import RoutingRepository
from agentgw.infrastructure.persistence.base import SessionLocal
from agentgw.infrastructure.persistence.models import RoutingModel


class SqlAlchemyRoutingRepository(RoutingRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, route_rule: RouteRule) -> RouteRule:
        with self._session_factory() as session:
            row = RoutingModel(
                route_id=uuid4().hex,
                channel_type=route_rule.channel_type,
                tenant_id=route_rule.tenant_id,
                scene=route_rule.scene,
                bot_id=route_rule.bot_id,
                agent_endpoint_id=route_rule.agent_endpoint_id,
            )
            session.add(row)
            session.commit()
            return route_rule
