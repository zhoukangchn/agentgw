from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agentgw"
    database_url: str = "sqlite+pysqlite:///./agentgw.db"
    agent_base_url: str = "ws://localhost:9000/ws"
    scheduler_enabled: bool = True
    message_sync_interval_seconds: int = 10
    contact_sync_interval_seconds: int = 300
    message_sync_targets: str = ""
    contact_sync_targets: str = ""
    feishu_access_token: str | None = None
    feishu_default_chat_id: str | None = None
    feishu_department_id: str | None = None
    wecom_access_token: str | None = None
    wecom_audit_proxy: str | None = None
    wecom_follow_user_ids: str = ""

    model_config = SettingsConfigDict(env_prefix="AGENTGW_", extra="ignore")
