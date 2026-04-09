from __future__ import annotations

from importlib import import_module
from typing import Any

from agentgw.domain.agent.entities import AgentResult


class SdkSessionTransport:
    async def send(self, *, endpoint, channel, conversation, message) -> AgentResult:
        if not endpoint.sdk_module:
            raise RuntimeError(f"sdk_module is required for endpoint {endpoint.endpoint_id}")

        module = import_module(endpoint.sdk_module)
        client_class = getattr(module, endpoint.sdk_client_class)
        event_type = getattr(module, endpoint.sdk_event_enum)
        client = client_class(endpoint.url)

        chunks: list[str] = []
        events: list[dict[str, Any]] = []

        @client.on(event_type.AGENT_CALL)
        async def on_agent_call(event: Any) -> None:
            events.append(
                {
                    "type": "agent_call",
                    "agent_name": getattr(event, "agent_name", "unknown"),
                    "is_start": bool(getattr(event, "is_start", False)),
                }
            )

        @client.on(event_type.AGENT)
        async def on_agent_text(event: Any) -> None:
            content = str(getattr(event, "content", ""))
            events.append({"type": "agent_text", "content": content})
            if content:
                chunks.append(content)

        @client.on(event_type.TOOL_EXECUTION)
        async def on_tool_execution(event: Any) -> None:
            events.append(
                {
                    "type": "tool_execution",
                    "tool_name": getattr(event, "tool_name", "unknown"),
                    "is_start": bool(getattr(event, "is_start", False)),
                    "result_summary": getattr(event, "result_summary", None),
                }
            )

        async with client:
            await client.send_config(
                {
                    "channel_id": channel.channel_id,
                    "conversation_id": conversation.conversation_id,
                }
            )
            await client.send_message(message.content)
            await client.wait_until_done()

        return AgentResult(
            endpoint_id=endpoint.endpoint_id,
            final_text="".join(chunks).strip(),
            raw_events=events,
        )
