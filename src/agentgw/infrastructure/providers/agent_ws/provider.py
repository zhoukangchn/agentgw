from __future__ import annotations

import asyncio
import inspect
import json
from contextlib import suppress
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
        event_handler: Callable[[Any], Any] | None = None,
    ):
        self._ws_url = ws_url
        self._timeout_seconds = timeout_seconds
        self._connect_factory = connect_factory or _default_connect
        self._event_handler = event_handler
        self._connection: Any | None = None
        self._connection_context: Any | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._pending_requests: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._send_lock = asyncio.Lock()

    async def _close_connection(self, failure: Exception | None = None) -> None:
        connection_context = self._connection_context
        reader_task = self._reader_task
        self._connection_context = None
        self._connection = None
        self._reader_task = None

        if reader_task is not None and reader_task is not asyncio.current_task():
            reader_task.cancel()
            with suppress(asyncio.CancelledError):
                await reader_task

        if failure is not None:
            await self._fail_pending_requests(failure)
        elif connection_context is not None:
            await self._fail_pending_requests(RuntimeError("websocket connection closed"))

        if connection_context is not None:
            with suppress(Exception):
                await connection_context.__aexit__(None, None, None)

    async def _fail_pending_requests(self, failure: Exception) -> None:
        pending_requests = self._pending_requests
        self._pending_requests = {}
        for future in pending_requests.values():
            if not future.done():
                future.set_exception(failure)

    async def _get_connection(self) -> Any:
        if self._connection is not None and not getattr(self._connection, "closed", False):
            if self._event_handler is not None and (self._reader_task is None or self._reader_task.done()):
                self._reader_task = asyncio.create_task(self._reader_loop(), name="agent-ws-reader")
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
        if self._event_handler is not None:
            self._reader_task = asyncio.create_task(self._reader_loop(), name="agent-ws-reader")
        return connection

    async def _reader_loop(self) -> None:
        websocket = self._connection
        if websocket is None:
            return

        try:
            while True:
                raw_payload = await websocket.recv()
                payload = json.loads(raw_payload)
                await self._handle_incoming_payload(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._close_connection(exc)

    async def _handle_incoming_payload(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            await self._dispatch_event(payload)
            return

        response_type = payload.get("type")
        request_id = payload.get("request_id")

        if response_type in {"send_message_result", "send_message_error"} and isinstance(request_id, str):
            future = self._pending_requests.pop(request_id, None)
            if future is None:
                if self._pending_requests:
                    failure = ValueError("unexpected websocket response request_id")
                    await self._close_connection(failure)
                return

            if response_type == "send_message_error":
                error_code = payload.get("error_code")
                error_message = payload.get("error_message")
                if not isinstance(error_code, str) or not isinstance(error_message, str):
                    future.set_exception(ValueError("invalid websocket error payload"))
                    return
                future.set_exception(WebSocketAgentError(error_code=error_code, error_message=error_message))
                return

            try:
                provider_message_id = payload["provider_message_id"]
                content = payload["content"]
            except KeyError as exc:
                future.set_exception(ValueError(f"missing websocket response field: {exc.args[0]}"))
                return

            future.set_result({"provider_message_id": provider_message_id, "content": content})
            return

        await self._dispatch_event(payload)

    async def _dispatch_event(self, payload: Any) -> None:
        if self._event_handler is None:
            return

        try:
            result = self._event_handler(payload)
            if inspect.isawaitable(result):
                await result
        except Exception:
            return

    async def _register_pending_request(self, request_id: str) -> asyncio.Future[dict[str, Any]]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_requests[request_id] = future
        return future

    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        async with self._send_lock:
            websocket = await self._get_connection()

            if self._event_handler is None:
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
                    await self._close_connection()
                    raise

                return SendMessageResponse(
                    provider_message_id=provider_message_id,
                    content=content,
                )

            future = await self._register_pending_request(request.request_id)

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
                response_payload = await asyncio.wait_for(future, timeout=self._timeout_seconds)
            except asyncio.TimeoutError as exc:
                self._pending_requests.pop(request.request_id, None)
                await self._close_connection(RuntimeError("websocket response timed out"))
                raise TimeoutError("websocket response timed out") from exc
            except WebSocketAgentError:
                self._pending_requests.pop(request.request_id, None)
                raise
            except Exception as exc:
                self._pending_requests.pop(request.request_id, None)
                await self._close_connection(exc)
                raise

        return SendMessageResponse(
            provider_message_id=response_payload["provider_message_id"],
            content=response_payload["content"],
        )
