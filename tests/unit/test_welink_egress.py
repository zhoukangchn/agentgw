from __future__ import annotations

import httpx
import pytest

from agentgw.adapters.egress import WeLinkHttpService, WeLinkMockService
from agentgw.bootstrap.container import build_welink_service
from agentgw.infrastructure.config.settings import Settings


@pytest.mark.asyncio
async def test_welink_http_service_posts_group_message_with_bearer_auth() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=200, json={"ok": True})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://welink.example.com",
    )
    service = WeLinkHttpService(
        base_url="https://welink.example.com",
        access_token="secret-token",
        client=client,
    )

    await service.send_group_message("group-123", "hello group")
    await client.aclose()

    assert service.group_messages == [{"group_id": "group-123", "content": "hello group"}]
    assert len(captured) == 1
    request = captured[0]
    assert str(request.url) == "https://welink.example.com/groups/group-123/messages"
    assert request.headers["Authorization"] == "Bearer secret-token"
    assert request.headers["Content-Type"] == "application/json"
    assert request.read() == b'{"msg_type":"text","content":"hello group"}'


@pytest.mark.asyncio
async def test_welink_http_service_posts_private_message_to_custom_path() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status_code=200, json={"ok": True})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://welink.example.com/api",
    )
    service = WeLinkHttpService(
        base_url="https://welink.example.com/api",
        access_token="secret-token",
        private_message_path="/messages/private/{conversation_id}",
        client=client,
    )

    await service.send_private_message("dm-456", "hello dm")
    await client.aclose()

    assert service.private_messages == [{"conversation_id": "dm-456", "content": "hello dm"}]
    assert len(captured) == 1
    request = captured[0]
    assert str(request.url) == "https://welink.example.com/api/messages/private/dm-456"
    assert request.read() == b'{"msg_type":"text","content":"hello dm"}'


def test_build_welink_service_returns_mock_service_in_mock_mode() -> None:
    service = build_welink_service(Settings())

    assert isinstance(service, WeLinkMockService)


def test_build_welink_service_requires_http_settings_for_http_mode() -> None:
    settings = Settings(welink_adapter_mode="http")

    with pytest.raises(RuntimeError, match="welink_base_url and welink_access_token are required"):
        build_welink_service(settings)


def test_build_welink_service_returns_http_service_in_http_mode() -> None:
    settings = Settings(
        welink_adapter_mode="http",
        welink_base_url="https://welink.example.com",
        welink_access_token="secret-token",
        welink_group_message_path="/custom/groups/{group_id}",
        welink_private_message_path="/custom/dms/{conversation_id}",
    )

    service = build_welink_service(settings)

    assert isinstance(service, WeLinkHttpService)
