from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any, Callable

from agentgw.domain.agent.contracts import SendMessageRequest, SendMessageResponse


class WebSocketAgentError(RuntimeError):
    def __init__(self, error_code: str, error_message: str):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"{error_code}: {error_message}")


def _default_connect(*args: Any, **kwargs: Any) -> Any:
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing
        raise RuntimeError("websockets dependency is required for WebSocketAgentProvider") from exc

    return websockets.connect(*args, **kwargs)


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
        self._connection: Any | None = None
        self._connection_context: Any | None = None
        self._send_lock = asyncio.Lock()

    async def _close_connection(self) -> None:
        if self._connection_context is None:
            return

        try:
            await self._connection_context.__aexit__(None, None, None)
        finally:
            self._connection_context = None
            self._connection = None

    async def _get_connection(self) -> Any:
        if self._connection is not None and not getattr(self._connection, "closed", False):
            return self._connection

        await self._close_connection()
        connection_context = self._connect_factory(
            self._ws_url,
            open_timeout=self._timeout_seconds,
            close_timeout=self._timeout_seconds,
        )
        connection = await connection_context.__aenter__()
        self._connection_context = connection_context
        self._connection = connection
        return connection

    async def _reset_connection(self) -> None:
        await self._close_connection()

    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        async with self._send_lock:
            websocket = await self._get_connection()

            try:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "send_message",
                            "request_id": request.request_id,
                            **asdict(request),
                        }
                    )
                )
                raw_payload = await asyncio.wait_for(websocket.recv(), timeout=self._timeout_seconds)
                payload = json.loads(raw_payload)

                if not isinstance(payload, dict):
                    raise ValueError("invalid websocket response payload")

                response_type = payload.get("type")
                if response_type == "send_message_error":
                    if payload.get("request_id") != request.request_id:
                        raise ValueError("unexpected websocket response request_id")
                    error_code = payload.get("error_code")
                    error_message = payload.get("error_message")
                    if not isinstance(error_code, str) or not isinstance(error_message, str):
                        raise ValueError("invalid websocket error payload")
                    raise WebSocketAgentError(error_code=error_code, error_message=error_message)

                if response_type != "send_message_result":
                    raise ValueError("unexpected websocket response type")
                if payload.get("request_id") != request.request_id:
                    raise ValueError("unexpected websocket response request_id")

                try:
                    provider_message_id = payload["provider_message_id"]
                    content = payload["content"]
                except KeyError as exc:
                    raise ValueError(f"missing websocket response field: {exc.args[0]}") from exc
            except WebSocketAgentError:
                raise
            except Exception:
                await self._reset_connection()
                raise

        return SendMessageResponse(
            provider_message_id=provider_message_id,
            content=content,
        )
