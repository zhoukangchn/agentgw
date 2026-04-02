from __future__ import annotations

import json
from typing import Any, Callable

from agentgw.domain.agent.contracts import SendMessageRequest, SendMessageResponse


def _default_connect() -> Any:
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing
        raise RuntimeError("websockets dependency is required for WebSocketAgentProvider") from exc

    return websockets.connect


class WebSocketAgentProvider:
    def __init__(
        self,
        ws_url: str,
        timeout_seconds: int = 10,
        connect_factory: Callable[..., Any] | None = None,
    ):
        self._ws_url = ws_url
        self._timeout_seconds = timeout_seconds
        self._connect_factory = connect_factory or _default_connect

    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        async with self._connect_factory(
            self._ws_url,
            open_timeout=self._timeout_seconds,
            close_timeout=self._timeout_seconds,
        ) as websocket:
            await websocket.send(json.dumps(request.__dict__))
            payload = json.loads(await websocket.recv())

        return SendMessageResponse(
            provider_message_id=payload["provider_message_id"],
            content=payload["content"],
        )
