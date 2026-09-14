from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.conversations.types import ConversationStatus, MessageKind, MessageRole
from app.http.schemas import (
    InboundRequest,
    InboundResponse,
    InteractiveRequest,
    InteractiveResponse,
)
from app.queue import buffer as message_buffer
from app.queue.enqueue import enqueue_button, enqueue_text

router = APIRouter(tags=["inbound"])


def _state(request: Request):
    return request.app.state.app_state


@router.post("/inbound", response_model=InboundResponse, response_model_by_alias=True)
async def inbound(body: InboundRequest, request: Request) -> InboundResponse:
    state = _state(request)
    if body.wa_id:
        conversation = await state.store.find_or_create_open(body.wa_id)
        await state.store.insert_message(
            conversation_id=conversation.id,
            role=MessageRole.CUSTOMER,
            kind=MessageKind.TEXT,
            body=body.text,
            payload={},
            source="inbound",
        )
        human_owned = conversation.status in (
            ConversationStatus.WAITING_HUMAN,
            ConversationStatus.HUMAN_ACTIVE,
        )
        if not human_owned:
            await message_buffer.push_text(state.redis, conversation.id, body.text)
            await enqueue_text(
                state.arq,
                conversation_id=conversation.id,
                agent_id=body.agent_id,
                buffer_ms=state.settings.buffer_ms,
                queue_name=state.settings.queue_name,
            )
        return InboundResponse(
            conversation_id=conversation.id,
            status=conversation.status.value,
            accepted=True,
        )

    if not body.session_id:
        raise HTTPException(status_code=422, detail="waId or sessionId is required")

    # Legacy sync demo path — not decision evidence
    await state.host.inbound(body.session_id, body.text, agent_id=body.agent_id or "amaru")
    return InboundResponse(
        conversation_id=body.session_id,
        status="BOT_AUTO",
        accepted=True,
    )


@router.post(
    "/inbound/interactive",
    response_model=InteractiveResponse,
    response_model_by_alias=True,
)
async def interactive(body: InteractiveRequest, request: Request) -> InteractiveResponse:
    state = _state(request)
    conversation_id = body.conversation_id or body.session_id
    if not conversation_id:
        raise HTTPException(status_code=422, detail="conversationId or sessionId is required")

    if body.conversation_id:
        conversation = await state.store.get_by_id(body.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail=f"Unknown conversationId: {body.conversation_id}")
        await enqueue_button(
            state.arq,
            conversation_id=body.conversation_id,
            button_id=body.button_id,
            agent_id=body.agent_id,
            queue_name=state.settings.queue_name,
        )
        return InteractiveResponse(conversation_id=body.conversation_id, accepted=True)

    await state.host.resume(conversation_id, body.button_id, agent_id=body.agent_id or "amaru")
    return InteractiveResponse(conversation_id=conversation_id, accepted=True)
