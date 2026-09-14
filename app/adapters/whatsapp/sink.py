from __future__ import annotations

from app.channel.types import ChannelMessage


class WhatsAppChannelSink:
    channel = "whatsapp"

    def __init__(self, wa: object) -> None:
        self._wa = wa

    async def deliver(self, message: ChannelMessage) -> None:
        if not message.target:
            return
        to = message.target
        send = getattr(self._wa, "send_message", None)
        send_buttons = getattr(self._wa, "send_message", None)
        # Prefer async methods when available
        if message.kind == "text":
            text = str(message.payload.get("text") or "")
            result = self._wa.send_message(to=to, text=text)  # type: ignore[attr-defined]
            if hasattr(result, "__await__"):
                await result  # type: ignore[misc]
            return
        if message.kind == "buttons":
            from pywa.types.callback import Button

            prompt = str(message.payload.get("prompt") or "")
            options = message.payload.get("options") or []
            buttons = [
                Button(title=str(opt.get("title") or opt.get("id")), callback_data=str(opt.get("id")))
                for opt in options[:3]
            ]
            result = self._wa.send_message(to=to, text=prompt, buttons=buttons)  # type: ignore[attr-defined]
            if hasattr(result, "__await__"):
                await result  # type: ignore[misc]
            return
        # list/location/media: best-effort text fallback for POC
        result = self._wa.send_message(to=to, text=str(message.payload))  # type: ignore[attr-defined]
        if hasattr(result, "__await__"):
            await result  # type: ignore[misc]
