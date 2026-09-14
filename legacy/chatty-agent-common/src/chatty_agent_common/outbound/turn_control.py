"""ADK turn control for outbound intent tools.

After ``reply_with_*`` / ``send_template``, Nest already has the WhatsApp
payload. Setting ``skip_summarization`` makes ADK treat the tool response as
a final event so the ReAct loop does not call more tools in the same turn.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.tool_context import ToolContext


def stop_turn_after_outbound_intent(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """``after_tool_callback``: end the turn after any outbound intent."""
    del tool, args  # signature fixed by ADK
    if isinstance(tool_response, dict) and tool_response.get("kind") in (
        "outbound_intent",
        "outbound_intent_batch",
    ):
        tool_context.actions.skip_summarization = True
    return None
