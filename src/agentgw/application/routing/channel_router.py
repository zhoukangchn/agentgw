from __future__ import annotations

from agentgw.domain.channel.entities import Channel


class ChannelRouter:
    def __init__(self, channel_repository) -> None:
        self._channel_repository = channel_repository

    def get_channel(self, channel_id: str) -> Channel:
        channel = self._channel_repository.get(channel_id)
        if not channel.enabled:
            raise LookupError(f"channel disabled: {channel_id}")
        return channel
