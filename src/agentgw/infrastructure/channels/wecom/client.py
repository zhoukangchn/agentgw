from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from agentgw.domain.contact.entities import ChannelContact
from agentgw.domain.message.entities import ChannelMessage

WECOM_CHATDATA_DOC_URL = "https://developer.work.weixin.qq.com/document/path/91774"
WECOM_EXTERNAL_CONTACT_LIST_DOC_URL = "https://developer.work.weixin.qq.com/document/path/92113"
WECOM_EXTERNAL_CONTACT_GET_DOC_URL = "https://developer.work.weixin.qq.com/document/path/92114"


class WeComApiError(RuntimeError):
    pass


class WeComClient:
    def __init__(
        self,
        access_token: str | None = None,
        *,
        base_url: str = "https://qyapi.weixin.qq.com",
        audit_proxy: str | None = None,
        follow_user_ids: list[str] | None = None,
        timeout_seconds: float = 10.0,
    ):
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._audit_proxy = audit_proxy
        self._follow_user_ids = follow_user_ids or []
        self._timeout_seconds = timeout_seconds

    async def fetch_messages(
        self,
        account_id: str,
        cursor_payload: dict[str, Any],
    ) -> tuple[list[ChannelMessage], dict[str, Any]]:
        if not self._access_token:
            return [], dict(cursor_payload)

        seq = int(cursor_payload.get("seq", 0))
        body: dict[str, Any] = {"seq": seq, "limit": int(cursor_payload.get("limit", 100))}
        if self._audit_proxy:
            body["proxy"] = self._audit_proxy

        payload = await self._post_json(
            f"/cgi-bin/msgaudit/get_chatdata?access_token={self._access_token}",
            json_body=body,
        )
        items = payload.get("chatdata", [])
        messages = [self._to_message(account_id, item) for item in items if isinstance(item, dict)]
        max_seq = max([seq, *[int(item.get("seq", 0)) for item in items if isinstance(item, dict)]])
        return messages, {"seq": max_seq}

    async def fetch_contacts(
        self,
        account_id: str,
        cursor_payload: dict[str, Any],
    ) -> tuple[list[ChannelContact], dict[str, Any]]:
        if not self._access_token or not self._follow_user_ids:
            return [], dict(cursor_payload)

        contacts: list[ChannelContact] = []
        for user_id in self._follow_user_ids:
            list_payload = await self._get_json(
                f"/cgi-bin/externalcontact/list?access_token={self._access_token}",
                params={"userid": user_id},
            )
            external_user_ids = list_payload.get("external_userid", [])
            for external_user_id in external_user_ids:
                detail_payload = await self._get_json(
                    f"/cgi-bin/externalcontact/get?access_token={self._access_token}",
                    params={"external_userid": external_user_id},
                )
                contacts.append(self._to_contact(account_id, detail_payload))
        return contacts, {"follow_user_ids": list(self._follow_user_ids)}

    async def _get_json(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_seconds) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        self._raise_for_business_error(payload)
        return payload

    async def _post_json(self, path: str, *, json_body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_seconds) as client:
            response = await client.post(path, json=json_body)
            response.raise_for_status()
            payload = response.json()
        self._raise_for_business_error(payload)
        return payload

    @staticmethod
    def _raise_for_business_error(payload: dict[str, Any]) -> None:
        errcode = payload.get("errcode")
        if errcode not in (None, 0):
            errmsg = payload.get("errmsg") or "wecom api request failed"
            raise WeComApiError(f"{errcode}: {errmsg}")

    @staticmethod
    def _to_message(account_id: str, item: dict[str, Any]) -> ChannelMessage:
        msgtime = item.get("msgtime")
        sent_at = datetime.fromtimestamp(int(msgtime), UTC) if msgtime else datetime.now(UTC)
        msgid = str(item.get("msgid", ""))
        return ChannelMessage(
            message_id=msgid,
            channel_type="wecom",
            account_id=account_id,
            conversation_id=str(item.get("roomid") or item.get("chatid") or ""),
            sender_id=str(item.get("from") or ""),
            sender_is_internal=not msgid.endswith("_external"),
            content=WeComClient._extract_text(item),
            sent_at=sent_at,
            raw_payload=item,
        )

    @staticmethod
    def _to_contact(account_id: str, payload: dict[str, Any]) -> ChannelContact:
        external_contact = payload.get("external_contact", {})
        return ChannelContact(
            contact_id=str(external_contact.get("external_userid") or ""),
            channel_type="wecom",
            account_id=account_id,
            display_name=str(external_contact.get("name") or ""),
            is_internal=False,
            raw_labels=["external"],
        )

    @staticmethod
    def _extract_text(item: dict[str, Any]) -> str:
        content = item.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            for key in ("content", "text", "title"):
                value = content.get(key)
                if isinstance(value, str):
                    return value
        return ""
