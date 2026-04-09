from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agentgw"
    database_url: str = "sqlite+pysqlite:///./agentgw.db"
    ws_agent_url: str = "ws://127.0.0.1:9000/ws"
    sdk_agent_url: str = "ws://127.0.0.1:9000/ws"
    sdk_module: str = "agentgw.dev.mock_relay_sdk"
    welink_adapter_mode: str = "mock"
    welink_base_url: str | None = None
    welink_access_token: str | None = None
    welink_group_message_path: str = "/groups/{group_id}/messages"
    welink_private_message_path: str = "/dms/{conversation_id}/messages"

    model_config = SettingsConfigDict(env_prefix="AGENTGW_", extra="ignore")
