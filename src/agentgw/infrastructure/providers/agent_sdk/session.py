from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from agentgw.domain.agent.events import AgentEvent, AgentEventType
from agentgw.domain.agent.sessions import AgentSession, EventHandler


class RelaySdkAgentSession:
    """Thin adapter over a session-oriented SDK client.

    This class intentionally does not import any specific SDK package. It wraps
    an already-constructed client object that follows the example shape:

    - async with client:
    - client.on(EventType.*)(handler)
    - await client.send_config(...)
    - await client.send_message(...)
    - await client.wait_until_done()
    """

    def __init__(self, client: Any, session_id: str | None = None) -> None:
        self._client = client
        self._session_id = session_id
        self._handlers: dict[str, list[EventHandler]] = {}

    def on(self, event_type: AgentEventType | str, handler: EventHandler) -> None:
        key = event_type.value if isinstance(event_type, AgentEventType) else str(event_type)
        self._handlers.setdefault(key, []).append(handler)

    def bind_sdk_event(self, event_type: Any, mapped_type: AgentEventType | str) -> Callable[[Callable[[Any], Any]], Callable[[Any], Any]]:
        """Register an SDK event with the underlying client and forward it to local handlers.

        The returned decorator can be used with SDKs that expose decorator-based
        subscriptions like `@client.on(EventType.AGENT)`.
        """

        key = mapped_type.value if isinstance(mapped_type, AgentEventType) else str(mapped_type)

        def decorator(callback: Callable[[Any], Any]) -> Callable[[Any], Any]:
            @self._client.on(event_type)
            async def _wrapped(event: Any) -> None:
                await self._dispatch(key, event)
                result = callback(event)
                if hasattr(result, "__await__"):
                    await result

            return callback

        return decorator

    async def _dispatch(self, event_key: str, event: Any) -> None:
        handlers = self._handlers.get(event_key, [])
        if not handlers:
            return

        agent_event = AgentEvent(
            session_id=self._session_id,
            event_type=AgentEventType(event_key) if event_key in AgentEventType._value2member_map_ else AgentEventType.DEBUG,
            payload=self._serialize_event(event),
            raw_payload=event,
        )
        for handler in handlers:
            result = handler(agent_event)
            if hasattr(result, "__await__"):
                await result

    async def __aenter__(self) -> "RelaySdkAgentSession":
        if hasattr(self._client, "__aenter__"):
            await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def send_config(self, config: dict[str, Any]) -> None:
        await self._client.send_config(config)

    async def send_message(self, message: str) -> None:
        await self._client.send_message(message)

    async def wait_until_done(self) -> None:
        await self._client.wait_until_done()

    async def close(self) -> None:
        if hasattr(self._client, "__aexit__"):
            await self._client.__aexit__(None, None, None)
            return
        if hasattr(self._client, "close"):
            result = self._client.close()
            if hasattr(result, "__await__"):
                await result

    @staticmethod
    def _serialize_event(event: Any) -> dict[str, Any]:
        if isinstance(event, dict):
            return event

        payload: dict[str, Any] = {}
        for name in dir(event):
            if name.startswith("_"):
                continue
            try:
                value = getattr(event, name)
            except Exception:
                continue
            if callable(value):
                continue
            payload[name] = value
        return payload
