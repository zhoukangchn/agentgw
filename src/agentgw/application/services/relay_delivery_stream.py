from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from agentgw.domain.delivery.entities import Delivery, DeliveryStatus
from agentgw.domain.delivery.repositories import DeliveryRepository
from agentgw.domain.message.repositories import MessageRepository
from agentgw.infrastructure.config.settings import Settings
from agentgw.infrastructure.providers.agent_sdk.loader import load_relay_sdk_client, load_relay_sdk_event_type
from agentgw.infrastructure.providers.agent_sdk.relay_bridge import RelaySdkBridge


@dataclass(slots=True)
class RelayDeliveryStreamRequest:
    delivery_id: str
    project_home: str | None = None
    timeout_seconds: int = 60


class RelayDeliveryStreamService:
    def __init__(
        self,
        *,
        settings: Settings,
        message_repository: MessageRepository,
        delivery_repository: DeliveryRepository,
        client_factory: Callable[..., Any] = load_relay_sdk_client,
        event_type_loader: Callable[..., Any] = load_relay_sdk_event_type,
    ) -> None:
        self._settings = settings
        self._message_repository = message_repository
        self._delivery_repository = delivery_repository
        self._client_factory = client_factory
        self._event_type_loader = event_type_loader

    async def stream_delivery(self, request: RelayDeliveryStreamRequest, http_request: Request) -> AsyncGenerator[str, None]:
        delivery = await self._delivery_repository.get_by_id(request.delivery_id)
        message = await self._message_repository.get_by_message_id(delivery.message_id)
        if delivery.status is DeliveryStatus.RECEIVED:
            delivery.mark_routed("relay_sdk")
            delivery = await self._delivery_repository.save(delivery)
        if delivery.status is DeliveryStatus.ROUTED:
            delivery.mark_dispatching()
            delivery = await self._delivery_repository.save(delivery)

        state: dict[str, Any] = {
            "reply_chunks": [],
            "delivery_id": delivery.delivery_id,
        }

        async def event_sink(event: str, data: dict[str, Any]) -> None:
            await self._apply_event(delivery, state, event, data)

        client = self._client_factory(
            self._settings.agent_base_url,
            module_path=self._settings.relay_sdk_module,
            client_class_name=self._settings.relay_sdk_client_class,
        )
        event_type = self._event_type_loader(
            module_path=self._settings.relay_sdk_module,
            enum_name=self._settings.relay_sdk_event_enum,
        )
        bridge = RelaySdkBridge(
            ws_url=self._settings.agent_base_url,
            message=message.content,
            project_home=request.project_home,
            timeout_seconds=request.timeout_seconds,
            client=client,
            event_type=event_type,
            event_sink=event_sink,
        )
        async for chunk in bridge.stream(http_request):
            yield chunk

    async def _apply_event(
        self,
        delivery: Delivery,
        state: dict[str, Any],
        event: str,
        data: dict[str, Any],
    ) -> None:
        if event == "debug" and data.get("step") == "message_sent" and delivery.status is DeliveryStatus.DISPATCHING:
            delivery.mark_dispatched()
            await self._delivery_repository.save(delivery)
            return

        if event in {"agent_call", "agent_text", "tool_execution", "tool"} and delivery.status is DeliveryStatus.DISPATCHED:
            delivery.mark_replying()
            await self._delivery_repository.save(delivery)

        if event == "agent_text":
            content = str(data.get("content", ""))
            if content:
                state["reply_chunks"].append(content)
            return

        if event == "done":
            status = str(data.get("status", ""))
            if status == "completed":
                reply_content = "".join(state["reply_chunks"]).strip()
                if not reply_content:
                    reply_content = ""
                if delivery.status in {DeliveryStatus.DISPATCHED, DeliveryStatus.REPLYING}:
                    delivery.mark_succeeded(reply_content)
                    await self._delivery_repository.save(delivery)
                return

            if status in {"timeout", "error"}:
                if delivery.status in {
                    DeliveryStatus.ROUTED,
                    DeliveryStatus.DISPATCHING,
                    DeliveryStatus.DISPATCHED,
                    DeliveryStatus.REPLYING,
                }:
                    delivery.mark_failed(str(data.get("message", status)))
                    await self._delivery_repository.save(delivery)
