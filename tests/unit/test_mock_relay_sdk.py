from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
import websockets

from agentgw.dev.mock_relay_sdk import EventType, RelayClient


@pytest_asyncio.fixture
async def relay_sdk_server() -> AsyncIterator[dict[str, object]]:
    calls: list[dict[str, object]] = []

    async def handler(websocket) -> None:
        config_payload = json.loads(await websocket.recv())
        calls.append(config_payload)

        message_payload = json.loads(await websocket.recv())
        calls.append(message_payload)

        await websocket.send(json.dumps({"type": "agent_call", "agent_name": "sdk-test-agent", "is_start": True}))
        await websocket.send(
            json.dumps({"type": "tool_execution", "tool_name": "lookup", "is_start": False, "result_summary": "ok"})
        )
        await websocket.send(json.dumps({"type": "agent_text", "content": "hello "}))
        await websocket.send(json.dumps({"type": "agent_text", "content": "sdk"}))
        await websocket.send(json.dumps({"type": "done", "status": "completed"}))

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield {"url": f"ws://127.0.0.1:{port}", "calls": calls}
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_relay_client_receives_full_session_event_stream(relay_sdk_server) -> None:
    seen: list[tuple[str, object]] = []
    client = RelayClient(relay_sdk_server["url"])

    @client.on(EventType.AGENT_CALL)
    async def on_agent_call(event) -> None:
        seen.append(("agent_call", event.agent_name))

    @client.on(EventType.TOOL_EXECUTION)
    async def on_tool(event) -> None:
        seen.append(("tool_execution", event.result_summary))

    @client.on(EventType.AGENT)
    async def on_agent_text(event) -> None:
        seen.append(("agent_text", event.content))

    async with client:
        await client.send_config({"channel_id": "welink_dm_twoway"})
        await client.send_message("sdk test")
        await client.wait_until_done()

    assert relay_sdk_server["calls"] == [
        {"type": "session_config", "config": {"channel_id": "welink_dm_twoway"}},
        {"type": "session_message", "message": "sdk test"},
    ]
    assert seen == [
        ("agent_call", "sdk-test-agent"),
        ("tool_execution", "ok"),
        ("agent_text", "hello "),
        ("agent_text", "sdk"),
    ]
