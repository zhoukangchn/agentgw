from __future__ import annotations

from pathlib import Path

from agentgw.bootstrap.container import build_app, build_container
from agentgw.infrastructure.config.settings import Settings


def make_app(tmp_path: Path, *, ws_url: str, sdk_url: str):
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'agentgw.db'}",
        ws_agent_url=ws_url,
        sdk_agent_url=sdk_url,
        sdk_module="agentgw.dev.mock_relay_sdk",
    )
    return build_app(build_container(settings))
