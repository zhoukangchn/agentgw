from pydantic import BaseModel


class RelayDeliveryStreamRequest(BaseModel):
    project_home: str | None = None
    timeout_seconds: int = 60
