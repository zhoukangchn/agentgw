from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def send_json(websocket: ServerConnection, payload: dict[str, Any]) -> None:
    await websocket.send(json.dumps(payload, ensure_ascii=False))


async def handle_rpc_message(websocket: ServerConnection, payload: dict[str, Any]) -> None:
    request_id = str(payload.get("request_id", ""))
    content = str(payload.get("content", ""))
    channel_id = str(payload.get("channel_id", "unknown"))
    conversation_id = str(payload.get("conversation_id", "unknown"))
    await send_json(
        websocket,
        {
            "type": "send_message_result",
            "request_id": request_id,
            "provider_message_id": f"mock-{request_id or 'message'}",
            "content": f"[mock-agent] rpc reply to {channel_id}/{conversation_id}: {content}",
        },
    )


async def handle_session_message(websocket: ServerConnection, payload: dict[str, Any], session_state: dict[str, Any]) -> None:
    message = str(payload.get("message", ""))
    await send_json(websocket, {"type": "agent_call", "agent_name": "mock-relay-agent", "is_start": True, "timestamp": utc_now()})
    await asyncio.sleep(0.05)
    await send_json(websocket, {"type": "tool_execution", "tool_name": "mock_lookup", "is_start": True, "result_summary": None, "timestamp": utc_now()})
    await asyncio.sleep(0.05)
    await send_json(websocket, {"type": "tool_execution", "tool_name": "mock_lookup", "is_start": False, "result_summary": "mock lookup finished", "timestamp": utc_now()})
    await asyncio.sleep(0.05)
    for chunk in [
        "[mock-relay-agent] session reply begin. ",
        f"channel={session_state.get('channel_id', '<empty>')}. ",
        f"message={message}",
    ]:
        await send_json(websocket, {"type": "agent_text", "content": chunk, "timestamp": utc_now()})
        await asyncio.sleep(0.05)
    await send_json(websocket, {"type": "done", "status": "completed", "timestamp": utc_now()})


async def handle_connection(websocket: ServerConnection) -> None:
    session_state: dict[str, Any] = {}
    async for raw_message in websocket:
        payload = json.loads(raw_message)
        message_type = str(payload.get("type", ""))
        if message_type == "send_message":
            await handle_rpc_message(websocket, payload)
        elif message_type == "session_config":
            config = payload.get("config", {})
            session_state["channel_id"] = config.get("channel_id")
            session_state["conversation_id"] = config.get("conversation_id")
        elif message_type == "session_message":
            await handle_session_message(websocket, payload, session_state)
        else:
            await send_json(websocket, {"type": "error", "message": f"unsupported type: {message_type}"})


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    async with websockets.serve(handle_connection, args.host, args.port):
        print(f"mock agent listening on ws://{args.host}:{args.port}/ws")
        with suppress(asyncio.CancelledError):
            await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
