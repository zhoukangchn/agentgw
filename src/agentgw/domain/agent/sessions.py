from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from agentgw.domain.agent.events import AgentEvent, AgentEventType


EventHandler = Callable[[AgentEvent], Awaitable[None] | None]


class AgentSession(Protocol):
    """Event-driven agent session abstraction.

    A session is the shape needed by SDK-style agents that keep a live websocket
    open, emit unsolicited events, and only finish when the server says the run
    is complete.
    """

    def on(self, event_type: AgentEventType | str, handler: EventHandler) -> None:
        raise NotImplementedError

    async def send_config(self, config: dict[str, Any]) -> None:
        raise NotImplementedError

    async def send_message(self, message: str) -> None:
        raise NotImplementedError

    async def wait_until_done(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class AgentSessionFactory(Protocol):
    async def create(self, endpoint_id: str) -> AgentSession:
        raise NotImplementedError
