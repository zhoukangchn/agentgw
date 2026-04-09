from pydantic import BaseModel


class RelayChatRequest(BaseModel):
    message: str
    project_home: str | None = None
    timeout_seconds: int = 60
