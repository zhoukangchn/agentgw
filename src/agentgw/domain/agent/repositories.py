from typing import Protocol

from agentgw.domain.agent.entities import AgentEndpoint


class AgentRepository(Protocol):
    async def save(self, agent_endpoint: AgentEndpoint) -> AgentEndpoint:
        raise NotImplementedError
