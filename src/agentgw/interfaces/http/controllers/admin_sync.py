from fastapi import APIRouter, HTTPException, Request, status

from agentgw.interfaces.http.schemas.admin_sync import TriggerSyncRequest

router = APIRouter(prefix="/admin/sync", tags=["admin-sync"])


@router.post("/messages", status_code=status.HTTP_202_ACCEPTED)
async def trigger_message_sync(request: TriggerSyncRequest, http_request: Request) -> dict[str, object]:
    container = http_request.app.state.container
    try:
        await container.trigger_message_sync(request.account_id, request.channel_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"accepted": True, "account_id": request.account_id}


@router.post("/contacts", status_code=status.HTTP_202_ACCEPTED)
async def trigger_contact_sync(request: TriggerSyncRequest, http_request: Request) -> dict[str, object]:
    container = http_request.app.state.container
    try:
        await container.trigger_contact_sync(request.account_id, request.channel_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"accepted": True, "account_id": request.account_id}
