from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.helpers import make_app


@pytest.mark.asyncio
async def test_healthz_and_list_endpoints(tmp_path, ws_rpc_server, sdk_session_server) -> None:
    app = make_app(tmp_path, ws_url=ws_rpc_server["url"], sdk_url=sdk_session_server["url"])
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/healthz")
        channels = await client.get("/channels")
        endpoints = await client.get("/agent-endpoints")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    assert [item["channel_id"] for item in channels.json()["items"]] == [
        "feishu_ingress",
        "feishu_to_welink_group",
        "welink_dm_twoway",
    ]
    assert [item["ingress_type"] for item in channels.json()["items"]] == [
        "feishu",
        "feishu",
        "welink_dm",
    ]

    assert [item["endpoint_id"] for item in endpoints.json()["items"]] == [
        "agent_sdk_default",
        "agent_ws_default",
    ]
    assert [item["transport"] for item in endpoints.json()["items"]] == [
        "sdk_session",
        "ws_rpc",
    ]
