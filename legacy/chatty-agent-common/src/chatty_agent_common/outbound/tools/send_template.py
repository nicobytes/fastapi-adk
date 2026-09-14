"""Pure ADK tool: queue an approved WhatsApp template outbound intent."""

from __future__ import annotations

from typing import Any

from chatty_agent_common.outbound.models import IntentToolResult, TemplateIntent


def send_template(
    name: str,
    language: str,
    components: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Queue an approved WhatsApp template message (outside 24h window).

    Only use pre-approved template names. Nest validates and sends via Cloud API.
    """
    intent = TemplateIntent(
        name=name,
        language=language,
        components=components,
    )
    return IntentToolResult(intent=intent).to_response_dict()
