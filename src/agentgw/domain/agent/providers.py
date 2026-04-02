from typing import Protocol

from agentgw.domain.agent.contracts import SendMessageRequest, SendMessageResponse


class AgentProvider(Protocol):
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        raise NotImplementedError
