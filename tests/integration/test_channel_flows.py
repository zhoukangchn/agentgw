from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.helpers import make_app


@pytest.mark.asyncio
async def test_feishu_to_welink_group_uses_ws_rpc_and_emits_group_egress(tmp_path, ws_rpc_server, sdk_session_server) -> None:
    app = make_app(tmp_path, ws_url=ws_rpc_server["url"], sdk_url=sdk_session_server["url"])
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ingress/events",
            json={
                "channel_id": "feishu_to_welink_group",
                "source_account_id": "acc-feishu-default",
                "source_conversation_id": "feishu-chat-1",
                "sender_id": "feishu-user-1",
                "content": "飞书消息进入群",
            },
        )
        messages = await client.get("/messages")
        egress = await client.get("/egress/welink")

    assert response.status_code == 200
    payload = response.json()
    assert payload["channel_id"] == "feishu_to_welink_group"
    assert payload["endpoint_id"] == "agent_ws_default"
    assert payload["egress_count"] == 1
    assert payload["agent_text"] == "ws-reply:飞书消息进入群"

    assert ws_rpc_server["calls"][0]["channel_id"] == "feishu_to_welink_group"
    assert ws_rpc_server["calls"][0]["channel_mode"] == "oneway"
    assert ws_rpc_server["calls"][0]["content"] == "飞书消息进入群"

    items = messages.json()["items"]
    assert [item["direction"] for item in items] == ["inbound", "agent", "egress"]
    assert items[0]["channel_id"] == "feishu_to_welink_group"
    assert items[2]["sender_id"] == "welink_group"
    assert egress.json()["group_messages"] == [
        {"group_id": "welink-group-demo", "content": "ws-reply:飞书消息进入群"}
    ]


@pytest.mark.asyncio
async def test_welink_dm_twoway_uses_sdk_session_and_emits_private_egress(tmp_path, ws_rpc_server, sdk_session_server) -> None:
    app = make_app(tmp_path, ws_url=ws_rpc_server["url"], sdk_url=sdk_session_server["url"])
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ingress/events",
            json={
                "channel_id": "welink_dm_twoway",
                "source_account_id": "acc-welink-default",
                "source_conversation_id": "welink-dm-1",
                "sender_id": "welink-user-1",
                "content": "WeLink 私聊双向测试",
            },
        )
        messages = await client.get("/messages")
        egress = await client.get("/egress/welink")

    assert response.status_code == 200
    payload = response.json()
    assert payload["channel_id"] == "welink_dm_twoway"
    assert payload["endpoint_id"] == "agent_sdk_default"
    assert payload["egress_count"] == 1
    assert payload["agent_text"] == "relay-part-1 relay-part-2:WeLink 私聊双向测试"

    assert sdk_session_server["calls"][0]["type"] == "session_config"
    assert sdk_session_server["calls"][0]["config"]["channel_id"] == "welink_dm_twoway"
    assert sdk_session_server["calls"][1]["type"] == "session_message"
    assert sdk_session_server["calls"][1]["message"] == "WeLink 私聊双向测试"

    items = messages.json()["items"]
    assert [item["direction"] for item in items] == ["inbound", "agent", "egress"]
    assert items[0]["channel_id"] == "welink_dm_twoway"
    assert items[2]["sender_id"] == "welink_dm"
    assert egress.json()["private_messages"] == [
        {"conversation_id": "welink-dm-1", "content": "relay-part-1 relay-part-2:WeLink 私聊双向测试"}
    ]


@pytest.mark.asyncio
async def test_source_account_mismatch_returns_400(tmp_path, ws_rpc_server, sdk_session_server) -> None:
    app = make_app(tmp_path, ws_url=ws_rpc_server["url"], sdk_url=sdk_session_server["url"])
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ingress/events",
            json={
                "channel_id": "feishu_to_welink_group",
                "source_account_id": "wrong-account",
                "source_conversation_id": "feishu-chat-1",
                "sender_id": "feishu-user-1",
                "content": "should fail",
            },
        )

    assert response.status_code == 400
    assert "source account mismatch" in response.json()["detail"]
