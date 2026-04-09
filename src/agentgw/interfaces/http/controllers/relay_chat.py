from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from agentgw.infrastructure.providers.agent_sdk.relay_bridge import RelaySdkBridge
from agentgw.infrastructure.providers.agent_sdk.loader import (
    load_relay_sdk_client,
    load_relay_sdk_event_type,
)
from agentgw.interfaces.http.schemas.relay_chat import RelayChatRequest

router = APIRouter(prefix="/relay", tags=["relay-sdk"])


@router.post("/stream", status_code=status.HTTP_200_OK)
async def relay_stream(request: RelayChatRequest, http_request: Request) -> StreamingResponse:
    container = http_request.app.state.container
    settings = container.settings

    try:
        client = load_relay_sdk_client(
            settings.agent_base_url,
            module_path=settings.relay_sdk_module,
            client_class_name=settings.relay_sdk_client_class,
        )
        event_type = load_relay_sdk_event_type(
            module_path=settings.relay_sdk_module,
            enum_name=settings.relay_sdk_event_enum,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    bridge = RelaySdkBridge(
        ws_url=settings.agent_base_url,
        message=request.message,
        project_home=request.project_home,
        timeout_seconds=request.timeout_seconds,
        client=client,
        event_type=event_type,
    )

    return StreamingResponse(
        bridge.stream(http_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
