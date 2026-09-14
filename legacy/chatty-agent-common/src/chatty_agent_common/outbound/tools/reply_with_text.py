"""Pure ADK tool: queue a plain text outbound intent."""

from __future__ import annotations

from typing import Any

from chatty_agent_common.outbound.models import IntentToolResult, TextIntent


def reply_with_text(body: str) -> dict[str, Any]:
    """Queue a plain text reply for the channel adapter (WhatsApp / webchat).

    Prefer this for normal conversational replies. Nest sends the message;
    do not repeat the same body as final model text after calling this tool.
    """
    intent = TextIntent(body=body)
    return IntentToolResult(intent=intent).to_response_dict()
