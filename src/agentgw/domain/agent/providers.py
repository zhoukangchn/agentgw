from typing import Protocol

from agentgw.application.dto.messages import SendMessageRequest, SendMessageResponse


class AgentProvider(Protocol):
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        raise NotImplementedError
