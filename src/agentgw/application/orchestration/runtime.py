from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agentgw.domain.message.entities import Message, MessageDirection


@dataclass(slots=True)
class IngressRequest:
    channel_id: str
    source_account_id: str
    source_conversation_id: str
    sender_id: str
    content: str
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrchestrationResult:
    channel_id: str
    endpoint_id: str
    inbound_message: Message
    agent_message: Message
    egress_messages: list[Message]
    raw_agent_events: list[dict[str, Any]]


class RuntimeOrchestrator:
    def __init__(
        self,
        *,
        channel_router,
        endpoint_repository,
        transport_registry,
        conversation_repository,
        message_repository,
        egress_dispatcher,
    ) -> None:
        self._channel_router = channel_router
        self._endpoint_repository = endpoint_repository
        self._transport_registry = transport_registry
        self._conversation_repository = conversation_repository
        self._message_repository = message_repository
        self._egress_dispatcher = egress_dispatcher

    async def handle_ingress(self, request: IngressRequest) -> OrchestrationResult:
        channel = self._channel_router.get_channel(request.channel_id)
        if request.source_account_id != channel.ingress.account_id:
            raise RuntimeError(
                f"source account mismatch for channel {channel.channel_id}: "
                f"expected {channel.ingress.account_id}, got {request.source_account_id}"
            )

        conversation = self._conversation_repository.get_or_create(
            channel_id=channel.channel_id,
            source_conversation_id=request.source_conversation_id,
            source_user_id=request.sender_id,
        )
        inbound_message = Message(
            message_id=f"msg_{uuid4().hex}",
            channel_id=channel.channel_id,
            conversation_id=conversation.conversation_id,
            sender_id=request.sender_id,
            direction=MessageDirection.INBOUND,
            content=request.content,
            raw_payload=request.raw_payload,
        )
        self._message_repository.add(inbound_message)

        endpoint = self._endpoint_repository.get(channel.agent.endpoint_id)
        transport = self._transport_registry.get(endpoint.transport.value)
        agent_result = await transport.send(
            endpoint=endpoint,
            channel=channel,
            conversation=conversation,
            message=inbound_message,
        )
        agent_message = Message(
            message_id=f"msg_{uuid4().hex}",
            channel_id=channel.channel_id,
            conversation_id=conversation.conversation_id,
            sender_id=endpoint.endpoint_id,
            direction=MessageDirection.AGENT,
            content=agent_result.final_text,
            raw_payload={"events": agent_result.raw_events},
        )
        self._message_repository.add(agent_message)

        egress_messages = await self._egress_dispatcher.dispatch(
            channel=channel,
            conversation=conversation,
            agent_message=agent_message,
        )
        for item in egress_messages:
            self._message_repository.add(item)

        return OrchestrationResult(
            channel_id=channel.channel_id,
            endpoint_id=endpoint.endpoint_id,
            inbound_message=inbound_message,
            agent_message=agent_message,
            egress_messages=egress_messages,
            raw_agent_events=agent_result.raw_events,
        )
