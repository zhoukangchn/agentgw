from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentgw.domain.agent.entities import AgentEndpoint
from agentgw.infrastructure.providers.agent_sdk.loader import load_relay_sdk_client
from agentgw.infrastructure.providers.agent_sdk.session import RelaySdkAgentSession
from agentgw.infrastructure.providers.agent_ws.provider import WebSocketAgentProvider


def build_agent_transport(
    endpoint: AgentEndpoint,
    *,
    client: Any | None = None,
    event_handler: Callable[[Any], Any] | None = None,
) -> Any:
    """Build an agent transport based on the endpoint type.

    This is the narrow integration seam for future agent implementations.
    """

    if endpoint.endpoint_type == "ws_rpc":
        return WebSocketAgentProvider(
            endpoint.base_url,
            timeout_seconds=endpoint.timeout_seconds,
            event_handler=event_handler,
        )

    if endpoint.endpoint_type == "relay_sdk":
        if client is None:
            client = load_relay_sdk_client(
                endpoint.base_url,
                module_path=str(endpoint.auth_config.get("relay_sdk_module", "your_sdk")),
                client_class_name=str(endpoint.auth_config.get("relay_sdk_client_class", "RelayClient")),
            )
        return RelaySdkAgentSession(client=client, session_id=endpoint.endpoint_id)

    raise ValueError(f"unsupported endpoint_type: {endpoint.endpoint_type}")
