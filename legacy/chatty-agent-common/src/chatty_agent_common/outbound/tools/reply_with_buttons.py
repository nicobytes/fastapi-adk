"""Pure ADK tool: queue an interactive buttons outbound intent."""

from __future__ import annotations

from typing import Any

from chatty_agent_common.outbound.models import (
    ButtonsIntent,
    IntentToolResult,
    ReplyButton,
)
from chatty_agent_common.outbound.tools._coerce import coerce_reply_button


def reply_with_buttons(
    body: str,
    buttons: list[dict[str, str] | str],
    header: str | None = None,
) -> dict[str, Any]:
    """Queue an interactive reply with up to 3 buttons (title max 20 chars).

    Each button needs ``id`` and ``title`` (dict, JSON object string, or a bare
    title string — Gemini sometimes omits the object shape). Nest renders
    WhatsApp interactive buttons; customer taps return as inbound interactive
    replies.
    """
    parsed = [ReplyButton.model_validate(coerce_reply_button(b)) for b in buttons]
    intent = ButtonsIntent(body=body, buttons=parsed, header=header)
    return IntentToolResult(intent=intent).to_response_dict()
