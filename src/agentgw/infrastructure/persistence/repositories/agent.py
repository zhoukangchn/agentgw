from agentgw.domain.agent.entities import AgentEndpoint
from agentgw.domain.agent.repositories import AgentRepository
from agentgw.infrastructure.persistence.base import SessionLocal


class SqlAlchemyAgentRepository(AgentRepository):
    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    async def save(self, agent_endpoint: AgentEndpoint) -> AgentEndpoint:
        with self._session_factory():
            return agent_endpoint
