from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agentgw.application.orchestration.runtime import IngressRequest

router = APIRouter()


class IngressEventBody(BaseModel):
    channel_id: str
    source_account_id: str
    source_conversation_id: str
    sender_id: str
    content: str = Field(min_length=1)


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/channels")
async def list_channels(request: Request):
    container = request.app.state.container
    return {
        "items": [
            {
                "channel_id": item.channel_id,
                "name": item.name,
                "ingress_type": item.ingress.type.value,
                "agent_endpoint_id": item.agent.endpoint_id,
                "egress_type": item.egress.type.value,
                "mode": item.mode.value,
                "enabled": item.enabled,
            }
            for item in container.channel_repository.list()
        ]
    }


@router.get("/agent-endpoints")
async def list_agent_endpoints(request: Request):
    container = request.app.state.container
    return {
        "items": [
            {
                "endpoint_id": item.endpoint_id,
                "name": item.name,
                "transport": item.transport.value,
                "url": item.url,
                "enabled": item.enabled,
            }
            for item in container.endpoint_repository.list()
        ]
    }


@router.get("/messages")
async def list_messages(request: Request):
    container = request.app.state.container
    return {
        "items": [
            {
                "message_id": item.message_id,
                "channel_id": item.channel_id,
                "conversation_id": item.conversation_id,
                "sender_id": item.sender_id,
                "direction": item.direction.value,
                "content": item.content,
                "created_at": item.created_at.isoformat(),
            }
            for item in container.message_repository.list()
        ]
    }


@router.get("/egress/welink")
async def list_welink_egress(request: Request):
    container = request.app.state.container
    return {
        "group_messages": container.welink_service.group_messages,
        "private_messages": container.welink_service.private_messages,
    }


@router.post("/ingress/events")
async def ingest_event(body: IngressEventBody, request: Request):
    container = request.app.state.container
    try:
        result = await container.runtime.handle_ingress(
            IngressRequest(
                channel_id=body.channel_id,
                source_account_id=body.source_account_id,
                source_conversation_id=body.source_conversation_id,
                sender_id=body.sender_id,
                content=body.content,
            )
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "channel_id": result.channel_id,
        "endpoint_id": result.endpoint_id,
        "agent_text": result.agent_message.content,
        "egress_count": len(result.egress_messages),
        "raw_agent_events": result.raw_agent_events,
    }
