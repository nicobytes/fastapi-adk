from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.adk.events import preview_events
from app.constants import APP_NAME, USER_ID
from app.conversations.inbox_view import to_inbox
from app.conversations.types import ConversationStatus
from app.http.schemas import StatusResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/{conversation_id}/handoff", response_model=StatusResponse, response_model_by_alias=True)
async def handoff(conversation_id: str, request: Request) -> StatusResponse:
    state = request.app.state.app_state
    conversation = await state.store.get_by_id(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
    updated = await state.store.set_status(conversation_id, ConversationStatus.WAITING_HUMAN)
    return StatusResponse(conversation_id=updated.id, status=updated.status.value)


@router.post("/{conversation_id}/release", response_model=StatusResponse, response_model_by_alias=True)
async def release(conversation_id: str, request: Request) -> StatusResponse:
    state = request.app.state.app_state
    conversation = await state.store.get_by_id(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
    updated = await state.store.set_status(conversation_id, ConversationStatus.BOT_AUTO)
    return StatusResponse(conversation_id=updated.id, status=updated.status.value)


@router.post("/{conversation_id}/close", response_model=StatusResponse, response_model_by_alias=True)
async def close(conversation_id: str, request: Request) -> StatusResponse:
    state = request.app.state.app_state
    conversation = await state.store.get_by_id(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
    updated = await state.store.set_status(conversation_id, ConversationStatus.CLOSED)
    return StatusResponse(conversation_id=updated.id, status=updated.status.value)


@router.get("/{conversation_id}/debug")
async def debug(conversation_id: str, request: Request) -> dict:
    state = request.app.state.app_state
    conversation = await state.store.get_by_id(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")
    messages = await state.store.list_messages(conversation_id)
    session = await state.host.session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=conversation_id
    )
    events = session.events if session else []
    return {
        "conversation": {
            "id": conversation.id,
            "status": conversation.status.value,
            "waId": conversation.wa_id,
        },
        "messages": to_inbox(messages),
        "sessionEventCount": len(events),
        "sessionPreview": preview_events(list(events)),
    }
