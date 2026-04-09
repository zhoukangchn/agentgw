from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from agentgw.application.services.relay_delivery_stream import RelayDeliveryStreamRequest, RelayDeliveryStreamService
from agentgw.interfaces.http.schemas.relay_delivery import RelayDeliveryStreamRequest as RelayDeliveryStreamBody

router = APIRouter(prefix="/relay/deliveries", tags=["relay-delivery"])


@router.post("/{delivery_id}/stream", status_code=status.HTTP_200_OK)
async def stream_delivery(
    delivery_id: str,
    body: RelayDeliveryStreamBody,
    http_request: Request,
) -> StreamingResponse:
    container = http_request.app.state.container
    service: RelayDeliveryStreamService = container.relay_delivery_service
    try:
        stream_request = RelayDeliveryStreamRequest(
            delivery_id=delivery_id,
            project_home=body.project_home,
            timeout_seconds=body.timeout_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return StreamingResponse(
        service.stream_delivery(stream_request, http_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
