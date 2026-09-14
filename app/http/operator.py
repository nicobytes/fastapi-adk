from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.http.schemas import OperatorReplyRequest, OperatorReplyResponse

router = APIRouter(tags=["operator"])


@router.post(
    "/operator/reply",
    response_model=OperatorReplyResponse,
    response_model_by_alias=True,
)
async def operator_reply(
    body: OperatorReplyRequest, request: Request
) -> OperatorReplyResponse:
    state = request.app.state.app_state
    conversation_id = body.conversation_id or body.session_id
    if not conversation_id:
        raise HTTPException(status_code=422, detail="conversationId or sessionId is required")
    conversation = await state.store.get_by_id(conversation_id)
    if conversation is None and body.conversation_id:
        raise HTTPException(status_code=404, detail=f"Unknown conversationId: {conversation_id}")
    if conversation is None:
        # legacy session path
        state.channel.bind(conversation_id, "fake", None)
        await state.channel.send_text(conversation_id, body.text, role="operator")
        await state.host.append_operator_text(conversation_id, body.text)
    else:
        await state.turn_service.append_operator_reply(conversation_id, body.text)
    return OperatorReplyResponse(conversation_id=conversation_id, accepted=True)
