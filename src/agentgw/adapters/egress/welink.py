from __future__ import annotations

from typing import Any

import httpx


class WeLinkMockService:
    def __init__(self) -> None:
        self.group_messages: list[dict[str, str]] = []
        self.private_messages: list[dict[str, str]] = []

    async def send_group_message(self, group_id: str, content: str) -> None:
        self.group_messages.append({"group_id": group_id, "content": content})

    async def send_private_message(self, conversation_id: str, content: str) -> None:
        self.private_messages.append({"conversation_id": conversation_id, "content": content})


class WeLinkHttpService:
    """Real WeLink egress adapter skeleton.

    This keeps the runtime-facing interface stable while isolating the eventual
    vendor-specific HTTP contract inside one adapter.
    """

    def __init__(
        self,
        *,
        base_url: str,
        access_token: str,
        group_message_path: str = "/groups/{group_id}/messages",
        private_message_path: str = "/dms/{conversation_id}/messages",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._access_token = access_token
        self._group_message_path = group_message_path
        self._private_message_path = private_message_path
        self._client = client
        self.group_messages: list[dict[str, str]] = []
        self.private_messages: list[dict[str, str]] = []

    async def send_group_message(self, group_id: str, content: str) -> None:
        payload = {"group_id": group_id, "content": content}
        self.group_messages.append(payload)
        await self._post(
            self._group_message_path.format(group_id=group_id),
            {"msg_type": "text", "content": content},
        )

    async def send_private_message(self, conversation_id: str, content: str) -> None:
        payload = {"conversation_id": conversation_id, "content": content}
        self.private_messages.append(payload)
        await self._post(
            self._private_message_path.format(conversation_id=conversation_id),
            {"msg_type": "text", "content": content},
        )

    async def _post(self, path: str, payload: dict[str, Any]) -> None:
        close_client = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(base_url=self._base_url, timeout=10)
            close_client = True
        try:
            response = await client.post(
                path,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
        finally:
            if close_client:
                await client.aclose()
