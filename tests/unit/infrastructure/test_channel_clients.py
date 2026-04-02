from __future__ import annotations

from types import SimpleNamespace

import pytest

from agentgw.infrastructure.channels.feishu.client import FeishuApiError, FeishuClient
from agentgw.infrastructure.channels.wecom.client import WeComApiError, WeComClient


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    def __init__(self, response_payload: dict):
        self._response_payload = response_payload

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, *args, **kwargs) -> FakeResponse:
        return FakeResponse(self._response_payload)

    async def post(self, *args, **kwargs) -> FakeResponse:
        return FakeResponse(self._response_payload)


@pytest.mark.asyncio
async def test_feishu_client_raises_on_business_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agentgw.infrastructure.channels.feishu.client.httpx.AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient({"code": 99991663, "msg": "invalid access token"}),
    )
    client = FeishuClient(access_token="token", default_chat_id="chat-1")

    with pytest.raises(FeishuApiError, match="99991663: invalid access token"):
        await client.fetch_messages("acc-1", {})


@pytest.mark.asyncio
async def test_wecom_client_raises_on_business_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agentgw.infrastructure.channels.wecom.client.httpx.AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient({"errcode": 40014, "errmsg": "invalid access token"}),
    )
    client = WeComClient(access_token="token")

    with pytest.raises(WeComApiError, match="40014: invalid access token"):
        await client.fetch_messages("acc-1", {})
