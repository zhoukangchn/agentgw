from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest_asyncio
import websockets


@pytest_asyncio.fixture
async def ws_rpc_server() -> AsyncIterator[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def handler(websocket):
        raw_request = await websocket.recv()
        payload = json.loads(raw_request)
        calls.append(payload)
        await websocket.send(
            json.dumps(
                {
                    "type": "send_message_result",
                    "request_id": payload["request_id"],
                    "provider_message_id": f"provider-{payload['request_id']}",
                    "content": f"ws-reply:{payload['content']}",
                },
                ensure_ascii=False,
            )
        )

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield {"url": f"ws://127.0.0.1:{port}", "calls": calls}
    finally:
        server.close()
        await server.wait_closed()


@pytest_asyncio.fixture
async def sdk_session_server() -> AsyncIterator[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def handler(websocket):
        raw_config = await websocket.recv()
        config_payload = json.loads(raw_config)
        calls.append(config_payload)

        raw_message = await websocket.recv()
        message_payload = json.loads(raw_message)
        calls.append(message_payload)

        await websocket.send(
            json.dumps(
                {"type": "agent_call", "agent_name": "mock-relay-agent", "is_start": True},
                ensure_ascii=False,
            )
        )
        await websocket.send(
            json.dumps(
                {"type": "tool_execution", "tool_name": "mock_lookup", "is_start": True, "result_summary": None},
                ensure_ascii=False,
            )
        )
        await websocket.send(
            json.dumps(
                {"type": "tool_execution", "tool_name": "mock_lookup", "is_start": False, "result_summary": "ok"},
                ensure_ascii=False,
            )
        )
        await websocket.send(
            json.dumps(
                {"type": "agent_text", "content": "relay-part-1 "},
                ensure_ascii=False,
            )
        )
        await websocket.send(
            json.dumps(
                {"type": "agent_text", "content": f"relay-part-2:{message_payload['message']}"},
                ensure_ascii=False,
            )
        )
        await websocket.send(
            json.dumps(
                {"type": "done", "status": "completed"},
                ensure_ascii=False,
            )
        )

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield {"url": f"ws://127.0.0.1:{port}", "calls": calls}
    finally:
        server.close()
        await server.wait_closed()
