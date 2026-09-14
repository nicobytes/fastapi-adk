"""Explicit opt-in registry for outbound intent tools."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Literal

from chatty_agent_common.outbound import tools as outbound_tools

OutboundToolName = Literal[
    "reply_with_text",
    "reply_with_buttons",
    "reply_with_list",
    "reply_with_location",
    "send_template",
]

_TOOL_MAP: dict[OutboundToolName, Callable[..., dict[str, Any]]] = {
    "reply_with_text": outbound_tools.reply_with_text,
    "reply_with_buttons": outbound_tools.reply_with_buttons,
    "reply_with_list": outbound_tools.reply_with_list,
    "reply_with_location": outbound_tools.reply_with_location,
    "send_template": outbound_tools.send_template,
}

DEFAULT_OUTBOUND_TOOLS: frozenset[OutboundToolName] = frozenset(
    {
        "reply_with_text",
        "reply_with_buttons",
        "reply_with_list",
        "reply_with_location",
    }
)


def get_outbound_intent_tools(
    enabled: Iterable[OutboundToolName] | None = None,
) -> list[Callable[..., dict[str, Any]]]:
    """Return ADK-callable tools for the requested capabilities (opt-in).

    Unknown names are ignored. Default enables text/buttons/list/location
    (not templates — agents must opt in to ``send_template``).
    """
    selected = set(enabled) if enabled is not None else set(DEFAULT_OUTBOUND_TOOLS)
    return [_TOOL_MAP[name] for name in _TOOL_MAP if name in selected]
