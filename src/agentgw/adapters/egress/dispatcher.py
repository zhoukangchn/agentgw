from __future__ import annotations

from uuid import uuid4

from agentgw.domain.channel.entities import EgressType
from agentgw.domain.message.entities import Message, MessageDirection


class EgressDispatcher:
    def __init__(self, welink_service) -> None:
        self._welink_service = welink_service

    async def dispatch(self, *, channel, conversation, agent_message) -> list[Message]:
        if channel.egress.type is EgressType.NONE:
            return []

        if channel.egress.type is EgressType.WELINK_GROUP:
            target_id = channel.egress.target_id
            if not target_id:
                raise RuntimeError(f"welink group target missing for channel {channel.channel_id}")
            await self._welink_service.send_group_message(target_id, agent_message.content)
            return [
                Message(
                    message_id=f"msg_{uuid4().hex}",
                    channel_id=channel.channel_id,
                    conversation_id=conversation.conversation_id,
                    sender_id="welink_group",
                    direction=MessageDirection.EGRESS,
                    content=agent_message.content,
                )
            ]

        if channel.egress.type is EgressType.WELINK_DM:
            target_id = conversation.source_conversation_id if channel.egress.use_source_conversation else channel.egress.target_id
            if not target_id:
                raise RuntimeError(f"welink dm target missing for channel {channel.channel_id}")
            await self._welink_service.send_private_message(target_id, agent_message.content)
            return [
                Message(
                    message_id=f"msg_{uuid4().hex}",
                    channel_id=channel.channel_id,
                    conversation_id=conversation.conversation_id,
                    sender_id="welink_dm",
                    direction=MessageDirection.EGRESS,
                    content=agent_message.content,
                )
            ]

        raise RuntimeError(f"unsupported egress type: {channel.egress.type}")
