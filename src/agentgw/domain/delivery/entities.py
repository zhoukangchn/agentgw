from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class DeliveryStatus(str, Enum):
    RECEIVED = "RECEIVED"
    ROUTED = "ROUTED"
    DISPATCHING = "DISPATCHING"
    DISPATCHED = "DISPATCHED"
    REPLYING = "REPLYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DEAD = "DEAD"


@dataclass
class Delivery:
    message_id: str
    delivery_id: str | None = None
    agent_endpoint_id: str | None = None
    status: DeliveryStatus = DeliveryStatus.RECEIVED
    attempt_count: int = 0
    last_error: str | None = None
    reply_content: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self._validate_state()

    @classmethod
    def create(cls, message_id: str) -> "Delivery":
        return cls(message_id=message_id)

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def _validate_state(self) -> None:
        if self.attempt_count < 0:
            raise ValueError("invalid delivery state")

        if self.status is DeliveryStatus.RECEIVED:
            if self.agent_endpoint_id is not None or self.reply_content is not None or self.last_error is not None:
                raise ValueError("invalid delivery state")
            return

        if self.status is DeliveryStatus.ROUTED:
            if self.agent_endpoint_id is None or self.reply_content is not None or self.last_error is not None:
                raise ValueError("invalid delivery state")
            return

        if self.status in {DeliveryStatus.DISPATCHING, DeliveryStatus.DISPATCHED, DeliveryStatus.REPLYING}:
            if self.agent_endpoint_id is None or self.reply_content is not None or self.last_error is not None:
                raise ValueError("invalid delivery state")
            return

        if self.status is DeliveryStatus.SUCCEEDED:
            if self.agent_endpoint_id is None or self.reply_content is None or self.last_error is not None:
                raise ValueError("invalid delivery state")
            return

        if self.status in {DeliveryStatus.FAILED, DeliveryStatus.DEAD}:
            if self.agent_endpoint_id is None or self.last_error is None or self.reply_content is not None:
                raise ValueError("invalid delivery state")
            return

        raise ValueError("invalid delivery state")

    def mark_routed(self, agent_endpoint_id: str) -> None:
        if self.status is not DeliveryStatus.RECEIVED:
            raise ValueError("invalid delivery transition")
        self.agent_endpoint_id = agent_endpoint_id
        self.status = DeliveryStatus.ROUTED
        self._touch()

    def mark_dispatching(self) -> None:
        if self.status is not DeliveryStatus.ROUTED:
            raise ValueError("invalid delivery transition")
        self.status = DeliveryStatus.DISPATCHING
        self._touch()

    def mark_dispatched(self) -> None:
        if self.status is not DeliveryStatus.DISPATCHING:
            raise ValueError("invalid delivery transition")
        self.status = DeliveryStatus.DISPATCHED
        self._touch()

    def mark_replying(self) -> None:
        if self.status is not DeliveryStatus.DISPATCHED:
            raise ValueError("invalid delivery transition")
        self.status = DeliveryStatus.REPLYING
        self._touch()

    def mark_succeeded(self, reply_content: str) -> None:
        if self.status not in {DeliveryStatus.DISPATCHED, DeliveryStatus.REPLYING}:
            raise ValueError("invalid delivery transition")
        self.reply_content = reply_content
        self.status = DeliveryStatus.SUCCEEDED
        self._touch()

    def mark_failed(self, last_error: str) -> None:
        if self.status not in {
            DeliveryStatus.ROUTED,
            DeliveryStatus.DISPATCHING,
            DeliveryStatus.DISPATCHED,
            DeliveryStatus.REPLYING,
        }:
            raise ValueError("invalid delivery transition")
        self.last_error = last_error
        self.status = DeliveryStatus.FAILED
        self._touch()

    def mark_dead(self) -> None:
        if self.status is not DeliveryStatus.FAILED:
            raise ValueError("invalid delivery transition")
        self.status = DeliveryStatus.DEAD
        self._touch()
