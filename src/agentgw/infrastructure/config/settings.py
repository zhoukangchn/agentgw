from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agentgw"
    database_url: str = "sqlite+pysqlite:///./agentgw.db"
    ws_agent_url: str = "ws://127.0.0.1:9000/ws"
    sdk_agent_url: str = "ws://127.0.0.1:9000/ws"
    sdk_module: str = "agentgw.dev.mock_relay_sdk"

    model_config = SettingsConfigDict(env_prefix="AGENTGW_", extra="ignore")
