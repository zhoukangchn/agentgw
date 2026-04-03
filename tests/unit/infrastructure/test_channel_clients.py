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
async def test_feishu_client_extracts_text_content_from_message_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agentgw.infrastructure.channels.feishu.client.httpx.AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient(
            {
                "code": 0,
                "data": {
                    "items": [
                        {
                            "message_id": "om_123",
                            "chat_id": "oc_123",
                            "create_time": "1710000000000",
                            "sender": {"id": "ou_123"},
                            "body": {"content": '{"text":"hello from feishu"}'},
                        }
                    ],
                    "page_token": "next-token",
                },
            }
        ),
    )
    client = FeishuClient(access_token="token", default_chat_id="oc_123")

    messages, next_cursor = await client.fetch_messages("acc-1", {})

    assert len(messages) == 1
    assert messages[0].content == "hello from feishu"
    assert next_cursor["page_token"] == "next-token"


@pytest.mark.parametrize(
    ("message_type", "raw_content", "expected"),
    [
        ("text", '{"text":"hello"}', "hello"),
        (
            "post",
            {
                "zh_cn": {
                    "title": "日报",
                    "content": [[{"tag": "text", "text": "进度正常"}, {"tag": "a", "text": "详情"}]],
                }
            },
            "日报\n进度正常 详情",
        ),
        ("image", '{"image_key":"img_123"}', "[image] img_123"),
        ("file", '{"file_name":"spec.pdf","file_key":"file_123"}', "[file] spec.pdf"),
        ("audio", '{"file_key":"audio_123"}', "[audio] audio_123"),
        ("media", '{"file_name":"demo.mp4","file_key":"media_123"}', "[media] demo.mp4"),
        ("sticker", '{"file_key":"stk_123"}', "[sticker] stk_123"),
        ("share_chat", '{"chat_name":"研发群","chat_id":"oc_123"}', "[share_chat] 研发群"),
        ("share_user", '{"user_name":"Alice","user_id":"ou_123"}', "[share_user] Alice"),
        ("location", '{"name":"上海办公室","address":"世纪大道"}', "[location] 上海办公室 世纪大道"),
        ("system", '{"template":"张三加入群聊"}', "[system] 张三加入群聊"),
    ],
)
def test_feishu_client_extracts_supported_message_types(message_type: str, raw_content, expected: str) -> None:
    assert FeishuClient._extract_text_content(message_type, raw_content) == expected


@pytest.mark.asyncio
async def test_wecom_client_raises_on_business_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agentgw.infrastructure.channels.wecom.client.httpx.AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient({"errcode": 40014, "errmsg": "invalid access token"}),
    )
    client = WeComClient(access_token="token")

    with pytest.raises(WeComApiError, match="40014: invalid access token"):
        await client.fetch_messages("acc-1", {})
