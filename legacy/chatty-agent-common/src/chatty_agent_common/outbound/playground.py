"""ADK playground helpers: mirror outbound intents as model text.

When ``ADK_DEV_MODE=true``, Nest never runs the playground session, so the UI
only shows function-call events for ``reply_with_*`` (prompts forbid repeating
the body as final model text). These callbacks capture the intent preview and
append it as an extra model ``Content`` event so the chat bubble is visible.

Interactive intents (buttons/list) include option titles and ids in the preview
so playground debugging shows what WhatsApp would render as choices.

If the model already emits visible text, the preview is cleared so the
playground does not show a duplicate bubble.

Nest ignores model text when intents are present, so WhatsApp is unchanged.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from google.genai import types

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_response import LlmResponse
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.tool_context import ToolContext

PLAYGROUND_OUTBOUND_PREVIEW_KEY = "_playground_outbound_preview"


def is_adk_dev_mode() -> bool:
    return os.getenv("ADK_DEV_MODE", "").strip().lower() == "true"


def _body_text(intent: dict[str, Any]) -> str:
    body = intent.get("body")
    return body.strip() if isinstance(body, str) else ""


def _format_buttons_options(intent: dict[str, Any]) -> str:
    buttons = intent.get("buttons")
    if not isinstance(buttons, list):
        return ""
    chips: list[str] = []
    for button in buttons:
        if not isinstance(button, dict):
            continue
        title = button.get("title")
        button_id = button.get("id")
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(button_id, str) or not button_id.strip():
            continue
        chips.append(f"[{title.strip()} · {button_id.strip()}]")
    return " ".join(chips)


def _format_list_options(intent: dict[str, Any]) -> str:
    lines: list[str] = []
    label = intent.get("buttonLabel")
    if not isinstance(label, str) or not label.strip():
        label = intent.get("button_label")
    if isinstance(label, str) and label.strip():
        lines.append(f"[{label.strip()}]")

    sections = intent.get("sections")
    if not isinstance(sections, list):
        return "\n".join(lines)

    has_rows = False
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_title = section.get("title")
        rows = section.get("rows")
        if not isinstance(rows, list):
            continue
        row_lines: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = row.get("title")
            row_id = row.get("id")
            if not isinstance(title, str) or not title.strip():
                continue
            if not isinstance(row_id, str) or not row_id.strip():
                continue
            row_lines.append(f"• {title.strip()} ({row_id.strip()})")
        if not row_lines:
            continue
        has_rows = True
        if isinstance(section_title, str) and section_title.strip():
            lines.append(f"{section_title.strip()}:")
        lines.extend(row_lines)

    if not has_rows:
        return ""
    return "\n".join(lines)


def summarize_outbound_intent(intent: dict[str, Any]) -> str:
    """Human-readable playground preview (options appended for buttons/list)."""
    intent_type = intent.get("type")
    if intent_type == "text":
        return _body_text(intent)
    if intent_type == "buttons":
        body = _body_text(intent)
        options = _format_buttons_options(intent)
        if body and options:
            return f"{body}\n\n{options}"
        return body or options
    if intent_type == "list":
        body = _body_text(intent)
        options = _format_list_options(intent)
        if body and options:
            return f"{body}\n\n{options}"
        return body or options
    if intent_type == "location":
        name = intent.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        lat = intent.get("latitude")
        lng = intent.get("longitude")
        if lat is not None and lng is not None:
            return f"📍 {lat}, {lng}"
        return ""
    if intent_type == "template":
        name = intent.get("name")
        if isinstance(name, str) and name.strip():
            return f"[template:{name.strip()}]"
        return ""
    return ""


def _content_has_visible_text(content: types.Content | None) -> bool:
    if content is None or not content.parts:
        return False
    for part in content.parts:
        if getattr(part, "thought", None):
            continue
        text = getattr(part, "text", None)
        if isinstance(text, str) and text.strip():
            return True
    return False


def _intents_from_tool_response(tool_response: dict[str, Any]) -> list[dict[str, Any]]:
    kind = tool_response.get("kind")
    if kind == "outbound_intent":
        intent = tool_response.get("intent")
        return [intent] if isinstance(intent, dict) else []
    if kind == "outbound_intent_batch":
        intents = tool_response.get("intents")
        if not isinstance(intents, list):
            return []
        return [item for item in intents if isinstance(item, dict)]
    return []


def capture_outbound_for_playground(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> dict[str, Any] | None:
    """``after_tool_callback``: stash outbound intent preview in session state."""
    del tool, args  # signature fixed by ADK
    if not is_adk_dev_mode():
        return None
    if not isinstance(tool_response, dict):
        return None
    previews = [
        text
        for intent in _intents_from_tool_response(tool_response)
        if (text := summarize_outbound_intent(intent))
    ]
    if not previews:
        return None
    preview = "\n\n".join(previews)
    existing = tool_context.state.get(PLAYGROUND_OUTBOUND_PREVIEW_KEY, "") or ""
    if isinstance(existing, str) and existing.strip():
        tool_context.state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] = (
            f"{existing.strip()}\n\n{preview}"
        )
    else:
        tool_context.state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] = preview
    return None


def clear_outbound_preview_if_model_text(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """``after_model_callback``: skip mirror when the model already wrote text."""
    if not is_adk_dev_mode():
        return None
    if _content_has_visible_text(llm_response.content):
        callback_context.state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] = ""
    return None


def _session_has_model_text_since_last_user(
    callback_context: CallbackContext,
) -> bool:
    """True if the current turn already has a visible model text bubble."""
    session = getattr(callback_context, "session", None)
    events = getattr(session, "events", None) if session is not None else None
    if not events:
        return False
    for event in reversed(list(events)):
        content = getattr(event, "content", None)
        if content is None:
            continue
        role = getattr(content, "role", None)
        if role == "user":
            break
        if _content_has_visible_text(content):
            return True
    return False


def mirror_outbound_for_playground(
    callback_context: CallbackContext,
) -> types.Content | None:
    """``after_agent_callback``: emit preview as model text for the playground UI."""
    if not is_adk_dev_mode():
        return None
    preview = callback_context.state.get(PLAYGROUND_OUTBOUND_PREVIEW_KEY, "") or ""
    if not isinstance(preview, str) or not preview.strip():
        return None
    # Avoid duplicate bubbles when the model also wrote the same reply.
    if _session_has_model_text_since_last_user(callback_context):
        callback_context.state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] = ""
        return None
    callback_context.state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] = ""
    return types.Content(
        role="model",
        parts=[types.Part(text=preview.strip())],
    )
