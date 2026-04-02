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

    @classmethod
    def create(cls, message_id: str) -> "Delivery":
        return cls(message_id=message_id)

    def mark_routed(self, agent_endpoint_id: str) -> None:
        if self.status is not DeliveryStatus.RECEIVED:
            raise ValueError("invalid delivery transition")
        self.agent_endpoint_id = agent_endpoint_id
        self.status = DeliveryStatus.ROUTED
        self.updated_at = datetime.now(UTC)

    def mark_succeeded(self, reply_content: str) -> None:
        if self.status not in {DeliveryStatus.DISPATCHED, DeliveryStatus.REPLYING}:
            raise ValueError("invalid delivery transition")
        self.reply_content = reply_content
        self.status = DeliveryStatus.SUCCEEDED
        self.updated_at = datetime.now(UTC)
