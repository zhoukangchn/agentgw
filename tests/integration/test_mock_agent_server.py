from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
import websockets


def _get_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _wait_until_server_ready(url: str) -> None:
    for _ in range(50):
        try:
            async with websockets.connect(url):
                return
        except Exception:
            await asyncio.sleep(0.05)
    raise RuntimeError(f"mock agent server did not start: {url}")


@pytest_asyncio.fixture
async def mock_agent_server() -> AsyncIterator[str]:
    port = _get_free_port()
    repo_root = Path(__file__).resolve().parents[2]
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(repo_root / "scripts" / "mock_agent_server.py"),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"ws://127.0.0.1:{port}"
    try:
        await _wait_until_server_ready(url)
        yield url
    finally:
        process.terminate()
        await process.wait()


@pytest.mark.asyncio
async def test_mock_agent_server_supports_ws_rpc(mock_agent_server: str) -> None:
    async with websockets.connect(mock_agent_server) as websocket:
        await websocket.send(
            json.dumps(
                {
                    "type": "send_message",
                    "request_id": "req-1",
                    "channel_id": "feishu_to_welink_group",
                    "conversation_id": "conv-1",
                    "content": "hello agent",
                },
                ensure_ascii=False,
            )
        )
        payload = json.loads(await websocket.recv())

    assert payload["type"] == "send_message_result"
    assert payload["request_id"] == "req-1"
    assert payload["provider_message_id"] == "mock-req-1"
    assert payload["content"] == "[mock-agent] rpc reply to feishu_to_welink_group/conv-1: hello agent"


@pytest.mark.asyncio
async def test_mock_agent_server_supports_session_events(mock_agent_server: str) -> None:
    async with websockets.connect(mock_agent_server) as websocket:
        await websocket.send(
            json.dumps(
                {
                    "type": "session_config",
                    "config": {
                        "channel_id": "welink_dm_twoway",
                        "conversation_id": "conv-session-1",
                    },
                },
                ensure_ascii=False,
            )
        )
        await websocket.send(json.dumps({"type": "session_message", "message": "session hello"}, ensure_ascii=False))

        events: list[dict[str, object]] = []
        while True:
            payload = json.loads(await websocket.recv())
            events.append(payload)
            if payload.get("type") == "done":
                break

    assert [item["type"] for item in events] == [
        "agent_call",
        "tool_execution",
        "tool_execution",
        "agent_text",
        "agent_text",
        "agent_text",
        "done",
    ]
    assert events[0]["agent_name"] == "mock-relay-agent"
    assert events[3]["content"] == "[mock-relay-agent] session reply begin. "
    assert events[4]["content"] == "channel=welink_dm_twoway. "
    assert events[5]["content"] == "message=session hello"
