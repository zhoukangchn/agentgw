from agentgw.domain.agent.entities import AgentEndpoint
from agentgw.domain.agent.repositories import AgentRepository
from agentgw.infrastructure.persistence.base import SessionLocal
from agentgw.infrastructure.persistence.models import AgentModel


class SqlAlchemyAgentRepository(AgentRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, agent_endpoint: AgentEndpoint) -> AgentEndpoint:
        with self._session_factory() as session:
            row = session.get(AgentModel, agent_endpoint.endpoint_id)
            if row is None:
                row = AgentModel(endpoint_id=agent_endpoint.endpoint_id)

            row.endpoint_type = agent_endpoint.endpoint_type
            row.base_url = agent_endpoint.base_url
            row.auth_config = agent_endpoint.auth_config
            row.timeout_seconds = agent_endpoint.timeout_seconds
            session.add(row)
            session.commit()
            return agent_endpoint
