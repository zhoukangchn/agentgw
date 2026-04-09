from __future__ import annotations

import asyncio
import json

import websockets

from agentgw.domain.agent.entities import AgentResult


class WsRpcTransport:
    async def send(self, *, endpoint, channel, conversation, message) -> AgentResult:
        async with websockets.connect(endpoint.url, open_timeout=endpoint.timeout_seconds) as websocket:
            await websocket.send(
                json.dumps(
                    {
                        "type": "send_message",
                        "request_id": message.message_id,
                        "channel_id": channel.channel_id,
                        "channel_mode": channel.mode.value,
                        "message_id": message.message_id,
                        "conversation_id": conversation.conversation_id,
                        "sender_id": message.sender_id,
                        "content": message.content,
                    },
                    ensure_ascii=False,
                )
            )
            raw_response = await asyncio.wait_for(websocket.recv(), timeout=endpoint.timeout_seconds)
            response = json.loads(raw_response)
            if response.get("type") != "send_message_result":
                raise RuntimeError(f"unexpected ws_rpc response: {response}")
            return AgentResult(
                endpoint_id=endpoint.endpoint_id,
                final_text=str(response.get("content", "")),
                raw_events=[response],
            )
