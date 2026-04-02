from pydantic import BaseModel


class TriggerSyncRequest(BaseModel):
    account_id: str
    channel_type: str | None = None
