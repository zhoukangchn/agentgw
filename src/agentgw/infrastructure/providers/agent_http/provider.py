import httpx

from agentgw.domain.agent.contracts import SendMessageRequest, SendMessageResponse


class HttpAgentProvider:
    def __init__(self, base_url: str, timeout_seconds: int = 10):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)

    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        response = await self._client.post("/messages", json=request.__dict__)
        response.raise_for_status()
        payload = response.json()
        return SendMessageResponse(
            provider_message_id=payload["provider_message_id"],
            content=payload["content"],
        )
