from dataclasses import dataclass, field


@dataclass
class SendMessageRequest:
    request_id: str
    channel_type: str
    tenant_id: str
    message_id: str
    sender_id: str
    conversation_id: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class SendMessageResponse:
    provider_message_id: str
    content: str
