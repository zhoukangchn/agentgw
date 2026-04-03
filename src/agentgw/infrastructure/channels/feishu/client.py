from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx

from agentgw.domain.contact.entities import ChannelContact
from agentgw.domain.message.entities import ChannelMessage

FEISHU_MESSAGE_LIST_DOC_URL = "https://open.feishu.cn/document/server-docs/im-v1/message/list?lang=zh-CN"
FEISHU_DEPARTMENT_USERS_DOC_URL = "https://open.feishu.cn/document/server-docs/contact-v3/user/find_by_department?lang=zh-CN"


class FeishuApiError(RuntimeError):
    pass


class FeishuClient:
    def __init__(
        self,
        access_token: str | None = None,
        *,
        base_url: str = "https://open.feishu.cn",
        default_chat_id: str | None = None,
        department_id: str | None = None,
        timeout_seconds: float = 10.0,
    ):
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._default_chat_id = default_chat_id
        self._department_id = department_id
        self._timeout_seconds = timeout_seconds

    async def fetch_messages(
        self,
        account_id: str,
        cursor_payload: dict[str, Any],
    ) -> tuple[list[ChannelMessage], dict[str, Any]]:
        chat_id = cursor_payload.get("container_id") or self._default_chat_id
        if not self._access_token or not isinstance(chat_id, str):
            return [], dict(cursor_payload)

        params: dict[str, Any] = {
            "container_id_type": cursor_payload.get("container_id_type", "chat"),
            "container_id": chat_id,
            "sort_type": cursor_payload.get("sort_type", "ByCreateTimeAsc"),
        }
        for key in ("page_token", "start_time", "end_time", "page_size"):
            value = cursor_payload.get(key)
            if value is not None:
                params[key] = value

        payload = await self._get_json("/open-apis/im/v1/messages", params=params)
        items = payload.get("data", {}).get("items", [])
        messages = [self._to_message(account_id, item) for item in items if isinstance(item, dict)]
        next_cursor = {
            "container_id": chat_id,
            "container_id_type": params["container_id_type"],
            "sort_type": params["sort_type"],
        }
        page_token = payload.get("data", {}).get("page_token")
        if isinstance(page_token, str):
            next_cursor["page_token"] = page_token
        return messages, next_cursor

    async def fetch_contacts(
        self,
        account_id: str,
        cursor_payload: dict[str, Any],
    ) -> tuple[list[ChannelContact], dict[str, Any]]:
        department_id = cursor_payload.get("department_id") or self._department_id
        if not self._access_token or not isinstance(department_id, str):
            return [], dict(cursor_payload)

        params: dict[str, Any] = {
            "department_id": department_id,
            "page_size": cursor_payload.get("page_size", 50),
            "user_id_type": cursor_payload.get("user_id_type", "open_id"),
        }
        page_token = cursor_payload.get("page_token")
        if isinstance(page_token, str):
            params["page_token"] = page_token

        payload = await self._get_json("/open-apis/contact/v3/users/find_by_department", params=params)
        items = payload.get("data", {}).get("items", [])
        contacts = [self._to_contact(account_id, item) for item in items if isinstance(item, dict)]
        next_cursor = {"department_id": department_id, "user_id_type": params["user_id_type"]}
        next_page_token = payload.get("data", {}).get("page_token")
        if isinstance(next_page_token, str):
            next_cursor["page_token"] = next_page_token
        return contacts, next_cursor

    async def _get_json(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_seconds) as client:
            response = await client.get(path, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        code = payload.get("code")
        if code not in (None, 0):
            message = payload.get("msg") or payload.get("message") or "feishu api request failed"
            raise FeishuApiError(f"{code}: {message}")
        return payload

    @staticmethod
    def _to_message(account_id: str, item: dict[str, Any]) -> ChannelMessage:
        sender = item.get("sender", {})
        body = item.get("body", {})
        message_type = item.get("message_type") or body.get("msg_type") or "text"
        create_time = item.get("create_time")
        sent_at = datetime.fromtimestamp(int(create_time) / 1000, UTC) if create_time else datetime.now(UTC)
        return ChannelMessage(
            message_id=str(item.get("message_id", "")),
            channel_type="feishu",
            account_id=account_id,
            conversation_id=str(item.get("chat_id") or item.get("conversation_id") or ""),
            sender_id=str(sender.get("id") or sender.get("sender_id") or ""),
            sender_is_internal=True,
            content=FeishuClient._extract_text_content(str(message_type), body.get("content") or item.get("body", "")),
            sent_at=sent_at,
            raw_payload=item,
        )

    @staticmethod
    def _extract_text_content(message_type: str, raw_content: Any) -> str:
        payload = FeishuClient._normalize_content_payload(raw_content)

        if message_type == "text":
            return FeishuClient._pick_string(payload, "text") or FeishuClient._stringify_payload(payload)
        if message_type == "post":
            return FeishuClient._extract_post_content(payload)
        if message_type == "image":
            return f"[image] {FeishuClient._pick_string(payload, 'image_key') or 'image'}"
        if message_type == "file":
            return f"[file] {FeishuClient._pick_string(payload, 'file_name', 'file_key') or 'file'}"
        if message_type == "audio":
            return f"[audio] {FeishuClient._pick_string(payload, 'file_key') or 'audio'}"
        if message_type == "media":
            return f"[media] {FeishuClient._pick_string(payload, 'file_name', 'file_key') or 'media'}"
        if message_type == "sticker":
            return f"[sticker] {FeishuClient._pick_string(payload, 'file_key', 'emoji_type') or 'sticker'}"
        if message_type == "share_chat":
            return f"[share_chat] {FeishuClient._pick_string(payload, 'chat_name', 'chat_id') or 'chat'}"
        if message_type == "share_user":
            return f"[share_user] {FeishuClient._pick_string(payload, 'user_name', 'user_id') or 'user'}"
        if message_type == "location":
            name = FeishuClient._pick_string(payload, "name", "title")
            address = FeishuClient._pick_string(payload, "address")
            joined = " ".join(part for part in (name, address) if part)
            return f"[location] {joined or 'location'}"
        if message_type == "system":
            return f"[system] {FeishuClient._pick_string(payload, 'template', 'text') or FeishuClient._stringify_payload(payload)}"

        text = FeishuClient._pick_string(payload, "text")
        if text:
            return text
        return FeishuClient._stringify_payload(payload)

    @staticmethod
    def _normalize_content_payload(raw_content: Any) -> Any:
        if isinstance(raw_content, str):
            try:
                return json.loads(raw_content)
            except json.JSONDecodeError:
                return raw_content
        return raw_content

    @staticmethod
    def _pick_string(payload: Any, *keys: str) -> str | None:
        if not isinstance(payload, dict):
            return None
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _extract_post_content(payload: Any) -> str:
        if not isinstance(payload, dict) or not payload:
            return FeishuClient._stringify_payload(payload)

        locale_payload = next((value for value in payload.values() if isinstance(value, dict)), None)
        if not isinstance(locale_payload, dict):
            return FeishuClient._stringify_payload(payload)

        title = locale_payload.get("title")
        lines: list[str] = []
        contents = locale_payload.get("content", [])
        if isinstance(contents, list):
            for paragraph in contents:
                if not isinstance(paragraph, list):
                    continue
                segments: list[str] = []
                for block in paragraph:
                    if isinstance(block, dict):
                        text = block.get("text")
                        if isinstance(text, str) and text:
                            segments.append(text)
                if segments:
                    lines.append(" ".join(segments))

        parts = [part for part in [title, *lines] if isinstance(part, str) and part]
        return "\n".join(parts) if parts else FeishuClient._stringify_payload(payload)

    @staticmethod
    def _stringify_payload(payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if payload is None:
            return ""
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _to_contact(account_id: str, item: dict[str, Any]) -> ChannelContact:
        labels = item.get("custom_attrs") or []
        return ChannelContact(
            contact_id=str(item.get("user_id") or item.get("open_id") or ""),
            channel_type="feishu",
            account_id=account_id,
            display_name=str(item.get("name") or item.get("display_name") or ""),
            is_internal=True,
            raw_labels=[str(label) for label in labels],
        )
