from __future__ import annotations

import logging
from collections.abc import Awaitable
from inspect import isawaitable
from typing import Any, TypeVar, cast

from app.conversations.types import ConversationStatus, MessageKind, MessageRole
from app.deps import AppState
from app.queue import buffer as message_buffer
from app.queue.enqueue import enqueue_button, enqueue_text

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def _maybe_await(value: object) -> None:
    if isawaitable(value):
        await cast(Awaitable[Any], value)


def register_handlers(wa: Any, state: AppState) -> None:
    @wa.on_message()
    async def on_message(_wa: Any, msg: Any) -> None:
        message_id = str(getattr(msg, "id", "") or "")
        if message_id and not await state.store.take_whatsapp_message(message_id):
            return
        sender = str(getattr(getattr(msg, "from_user", None), "wa_id", None) or getattr(msg, "from_user", "") or "")
        text = str(getattr(msg, "text", None) or getattr(msg, "caption", None) or "")
        if not sender or not text:
            # Button callbacks often arrive as callback_button
            return
        try:
            indicate = getattr(msg, "indicate_typing", None)
            if callable(indicate):
                await _maybe_await(indicate())
        except Exception:
            logger.exception("whatsapp typing indicator failed")

        conversation = await state.store.find_or_create_open(sender)
        await state.store.insert_message(
            conversation_id=conversation.id,
            role=MessageRole.CUSTOMER,
            kind=MessageKind.TEXT,
            body=text,
            payload={},
            source="whatsapp",
        )
        state.channel.bind(conversation.id, "whatsapp", sender)
        if conversation.status in (
            ConversationStatus.WAITING_HUMAN,
            ConversationStatus.HUMAN_ACTIVE,
        ):
            return
        await message_buffer.push_text(state.redis, conversation.id, text)
        await enqueue_text(
            state.arq,
            conversation_id=conversation.id,
            agent_id=state.settings.whatsapp_agent_id,
            buffer_ms=state.settings.buffer_ms,
            queue_name=state.settings.queue_name,
        )

    @wa.on_callback_button()
    async def on_button(_wa: Any, btn: Any) -> None:
        message_id = str(getattr(btn, "id", "") or getattr(btn, "message_id", "") or "")
        if message_id and not await state.store.take_whatsapp_message(message_id):
            return
        sender = str(getattr(getattr(btn, "from_user", None), "wa_id", None) or "")
        button_id = str(getattr(btn, "data", None) or getattr(btn, "callback_data", None) or "")
        if not sender or not button_id:
            return
        conversation = await state.store.find_or_create_open(sender)
        state.channel.bind(conversation.id, "whatsapp", sender)
        await enqueue_button(
            state.arq,
            conversation_id=conversation.id,
            button_id=button_id,
            agent_id=state.settings.whatsapp_agent_id,
            queue_name=state.settings.queue_name,
        )
