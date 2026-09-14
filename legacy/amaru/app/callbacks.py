"""Session bootstrap and tool guardrails for the Amaru orchestrator."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

_TURN_COUNT_KEY = "user_turn_count"
_ACTIVATE_PENDING_KEY = "activate_pending"


def _is_activate_pending(state: Mapping[str, Any]) -> bool:
    return str(state.get(_ACTIVATE_PENDING_KEY) or "").lower() == "true"


def seed_session_state(
    callback_context: CallbackContext,
) -> types.Content | None:
    """Initialize optional state keys and increment user turn count each turn."""
    state = callback_context.state
    state.setdefault("handoff_phase", "")
    state.setdefault("handoff_bridge_message", "")
    state.setdefault("qualification_score", "")
    state.setdefault("lead_qualifies", "")
    if _is_activate_pending(state):
        return None
    turn_count = int(state.get(_TURN_COUNT_KEY, 0) or 0) + 1
    state[_TURN_COUNT_KEY] = turn_count
    return None


def recover_unknown_tool_error(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> dict[str, str]:
    """Convert tool failures into a recoverable tool response.

    ADK invokes this both when the model calls a missing tool and when a
    registered tool raises. Only the missing-tool case should claim
    TOOL_NOT_FOUND — execution errors must surface the real message so the
    model can fix args instead of abandoning the tool.
    """
    del args, tool_context  # unused; signature fixed by ADK callback
    message = str(error)
    if "not found" in message.lower():
        return {
            "error": (
                f"La herramienta '{tool.name}' no existe. No la reintentes; "
                "escribe tu respuesta final directamente como texto."
            ),
            "error_code": "TOOL_NOT_FOUND",
        }
    return {
        "error": (
            f"Error al ejecutar '{tool.name}': {message}. "
            "Corrige los argumentos e inténtalo de nuevo, o responde en texto."
        ),
        "error_code": "TOOL_ERROR",
    }
