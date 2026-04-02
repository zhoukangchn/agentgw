from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SyncCursor:
    cursor_id: str
    channel_type: str
    account_id: str
    scope: str
    cursor_payload: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
