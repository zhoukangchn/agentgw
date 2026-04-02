from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChannelMessage:
    message_id: str
    channel_type: str
    account_id: str
    conversation_id: str
    sender_id: str
    sender_is_internal: bool
    content: str
    sent_at: datetime
    raw_payload: dict
