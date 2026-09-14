from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adk.host import AdkHost, RunView
from app.channel.service import ChannelService
from app.constants import DEFAULT_AGENT_ID, USER_ID
from app.conversations.store import ConversationStore
from app.conversations.types import MessageKind, MessageRole


@dataclass
class TurnResult:
    view: RunView | None = None
    skipped: bool = False
    reason: str | None = None
    stored: bool = False


class TurnService:
    """Called only from the queue worker — never from HTTP accept path."""

    def __init__(
        self,
        host: AdkHost,
        store: ConversationStore,
        channel: ChannelService,
    ) -> None:
        self.host = host
        self.store = store
        self.channel = channel
        self.fail_next_text_turn = False

    async def run_text_turn(
        self,
        *,
        conversation_id: str,
        text: str,
        agent_id: str | None = None,
    ) -> TurnResult:
        if self.fail_next_text_turn:
            self.fail_next_text_turn = False
            raise RuntimeError("simulated processor failure")
        conversation = await self.store.get_by_id(conversation_id)
        if conversation is None:
            raise KeyError(f"Conversation not found: {conversation_id}")
        self.channel.bind(conversation.id, "fake", conversation.wa_id)
        view = await self.host.inbound(
            conversation.id,
            text,
            agent_id=agent_id or DEFAULT_AGENT_ID,
            user_id=USER_ID,
            channel="fake",
            target=conversation.wa_id,
        )
        return TurnResult(view=view)

    async def run_button_turn(
        self,
        *,
        conversation_id: str,
        button_id: str,
        agent_id: str | None = None,
    ) -> TurnResult:
        conversation = await self.store.get_by_id(conversation_id)
        if conversation is None:
            raise KeyError(f"Conversation not found: {conversation_id}")
        self.channel.bind(conversation.id, "fake", conversation.wa_id)
        session = await self.host.ensure_session(
            conversation.id, agent_id=agent_id or DEFAULT_AGENT_ID
        )
        from app.adk.events import find_pending_choice

        pending = find_pending_choice(session.events)
        title = await self._option_title(conversation.id, button_id)
        await self.store.insert_message(
            conversation_id=conversation.id,
            role=MessageRole.CUSTOMER,
            kind=MessageKind.CHOICE,
            body=title or button_id,
            payload={"buttonId": button_id},
            source="inbound",
        )
        if not pending:
            return TurnResult(skipped=True, reason="no_pending_choice", stored=True)
        view = await self.host.resume(
            conversation.id,
            button_id,
            agent_id=agent_id or DEFAULT_AGENT_ID,
            user_id=USER_ID,
            channel="fake",
            target=conversation.wa_id,
        )
        return TurnResult(view=view, stored=True)

    async def append_operator_reply(self, conversation_id: str, text: str) -> None:
        conversation = await self.store.get_by_id(conversation_id)
        if conversation is None:
            raise KeyError(f"Conversation not found: {conversation_id}")
        self.channel.bind(conversation.id, "fake", conversation.wa_id)
        await self.channel.send_text(conversation.id, text, role="operator")
        # Channel dual-write already inserts bot/operator; fix role via dedicated insert
        # send_text with role=operator maps to OPERATOR in channel service
        await self.host.append_operator_text(conversation.id, text)

    async def _option_title(self, conversation_id: str, button_id: str) -> str | None:
        messages = await self.store.list_messages(conversation_id)
        for message in reversed(messages):
            if message.kind != MessageKind.BUTTONS:
                continue
            options = message.payload.get("options") or []
            for option in options:
                if option.get("id") == button_id:
                    return str(option.get("title") or button_id)
        for message in reversed(self.channel.list(conversation_id)):
            if message.kind != "buttons":
                continue
            options = message.payload.get("options") or []
            for option in options:
                if option.get("id") == button_id:
                    return str(option.get("title") or button_id)
        return None
