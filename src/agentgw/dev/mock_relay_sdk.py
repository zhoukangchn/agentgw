from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable

import websockets


class EventType(str, Enum):
    AGENT_CALL = "agent_call"
    AGENT = "agent_text"
    TOOL_EXECUTION = "tool_execution"


@dataclass(slots=True)
class AgentCallEvent:
    agent_name: str
    is_start: bool


@dataclass(slots=True)
class AgentTextEvent:
    content: str


@dataclass(slots=True)
class ToolExecutionEvent:
    tool_name: str
    is_start: bool
    result_summary: str | None = None


class RelayClient:
    def __init__(self, ws_url: str) -> None:
        self._ws_url = ws_url
        self._handlers: dict[str, list[Callable[[Any], Awaitable[None] | None]]] = {}
        self._connection = None
        self._connection_context = None
        self._reader_task: asyncio.Task[None] | None = None
        self._done = asyncio.Event()

    def on(self, event_type: EventType | str):
        key = event_type.value if isinstance(event_type, EventType) else str(event_type)

        def decorator(handler):
            self._handlers.setdefault(key, []).append(handler)
            return handler

        return decorator

    async def __aenter__(self):
        self._connection_context = websockets.connect(self._ws_url)
        self._connection = await self._connection_context.__aenter__()
        self._done.clear()
        self._reader_task = asyncio.create_task(self._reader_loop())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._connection_context is not None:
            await self._connection_context.__aexit__(exc_type, exc, tb)

    async def send_config(self, config: dict[str, Any]) -> None:
        await self._connection.send(json.dumps({"type": "session_config", "config": config}, ensure_ascii=False))

    async def send_message(self, message: str) -> None:
        await self._connection.send(json.dumps({"type": "session_message", "message": message}, ensure_ascii=False))

    async def wait_until_done(self) -> None:
        await self._done.wait()

    async def _reader_loop(self) -> None:
        async for raw in self._connection:
            payload = json.loads(raw)
            await self._dispatch(payload)

    async def _dispatch(self, payload: dict[str, Any]) -> None:
        event_type = str(payload.get("type", ""))
        if event_type == EventType.AGENT_CALL.value:
            event = AgentCallEvent(agent_name=str(payload.get("agent_name", "unknown")), is_start=bool(payload.get("is_start", False)))
        elif event_type == EventType.AGENT.value:
            event = AgentTextEvent(content=str(payload.get("content", "")))
        elif event_type == EventType.TOOL_EXECUTION.value:
            event = ToolExecutionEvent(
                tool_name=str(payload.get("tool_name", "unknown")),
                is_start=bool(payload.get("is_start", False)),
                result_summary=payload.get("result_summary"),
            )
        else:
            event = payload
        for handler in self._handlers.get(event_type, []):
            result = handler(event)
            if hasattr(result, "__await__"):
                await result
        if event_type == "done":
            self._done.set()
