from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ChannelContact:
    contact_id: str
    channel_type: str
    account_id: str
    display_name: str
    is_internal: bool
    raw_labels: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
