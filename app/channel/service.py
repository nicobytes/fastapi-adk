from __future__ import annotations

from typing import Any, Callable, Awaitable

from app.channel.types import ChannelMessage, ChannelSink
from app.conversations.store import ConversationStore
from app.conversations.types import ChoiceOption, MessageKind, MessageRole


class ChannelService:
    """Fake channel sink with dual-write to inbox."""

    channel = "fake"

    def __init__(self, store: ConversationStore) -> None:
        self._store = store
        self._log: list[ChannelMessage] = []
        self._bindings: dict[str, tuple[str, str | None]] = {}
        self._extra_sinks: list[ChannelSink] = []

    def add_sink(self, sink: ChannelSink) -> None:
        self._extra_sinks.append(sink)

    def bind(self, session_id: str, channel: str, target: str | None) -> None:
        self._bindings[session_id] = (channel, target)

    def list(self, session_id: str | None = None) -> list[ChannelMessage]:
        if session_id is None:
            return list(self._log)
        return [message for message in self._log if message.session_id == session_id]

    async def send_text(self, session_id: str, text: str, *, role: str = "bot") -> None:
        message = ChannelMessage(
            session_id=session_id,
            kind="text",
            payload={"text": text},
            target=self._target(session_id),
            channel=self._channel(session_id),
        )
        await self._push(message, role=role, kind=MessageKind.TEXT, body=text, payload={})

    async def send_buttons(
        self,
        session_id: str,
        prompt: str,
        options: list[ChoiceOption] | list[dict[str, str]],
        *,
        function_call_id: str | None = None,
        invocation_id: str | None = None,
    ) -> None:
        normalized = [
            ChoiceOption.model_validate(option) if not isinstance(option, ChoiceOption) else option
            for option in options
        ]
        payload: dict[str, Any] = {
            "prompt": prompt,
            "options": [{"id": option.id, "title": option.title} for option in normalized],
        }
        if function_call_id:
            payload["functionCallId"] = function_call_id
        if invocation_id:
            payload["invocationId"] = invocation_id
        message = ChannelMessage(
            session_id=session_id,
            kind="buttons",
            payload=payload,
            target=self._target(session_id),
            channel=self._channel(session_id),
        )
        await self._push(
            message,
            role="bot",
            kind=MessageKind.BUTTONS,
            body=prompt,
            payload=payload,
            source="ask_choice",
        )

    async def send_location(
        self,
        session_id: str,
        *,
        latitude: float,
        longitude: float,
        name: str = "",
        address: str = "",
    ) -> None:
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "name": name,
            "address": address,
        }
        body = name or f"{latitude},{longitude}"
        message = ChannelMessage(
            session_id=session_id,
            kind="location",
            payload=payload,
            target=self._target(session_id),
            channel=self._channel(session_id),
        )
        await self._push(
            message, role="bot", kind=MessageKind.LOCATION, body=body, payload=payload
        )

    async def send_media(
        self,
        session_id: str,
        *,
        url: str,
        mime_type: str,
        caption: str = "",
    ) -> None:
        payload = {"url": url, "mimeType": mime_type, "caption": caption}
        message = ChannelMessage(
            session_id=session_id,
            kind="media",
            payload=payload,
            target=self._target(session_id),
            channel=self._channel(session_id),
        )
        await self._push(
            message,
            role="bot",
            kind=MessageKind.MEDIA,
            body=caption or url,
            payload=payload,
        )

    async def _push(
        self,
        message: ChannelMessage,
        *,
        role: str,
        kind: MessageKind,
        body: str,
        payload: dict[str, Any],
        source: str | None = None,
    ) -> None:
        self._log.append(message)
        message_role = MessageRole.OPERATOR if role == "operator" else MessageRole.BOT
        if role == "customer":
            message_role = MessageRole.CUSTOMER
        await self._store.insert_message(
            conversation_id=message.session_id,
            role=message_role,
            kind=kind,
            body=body,
            payload=payload,
            source=source,
        )
        for sink in self._extra_sinks:
            await sink.deliver(message)

    def _target(self, session_id: str) -> str | None:
        binding = self._bindings.get(session_id)
        return binding[1] if binding else None

    def _channel(self, session_id: str) -> str:
        binding = self._bindings.get(session_id)
        return binding[0] if binding else "fake"
