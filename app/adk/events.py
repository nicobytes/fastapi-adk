from __future__ import annotations

from typing import Any, Iterable

from google.adk.events.event import Event


def find_pending_choice(events: Iterable[Any]) -> dict[str, Any] | None:
    """Find the latest unanswered ask_choice function call."""
    pending: dict[str, Any] | None = None
    answered: set[str] = set()
    for event in events:
        for part in getattr(getattr(event, "content", None), "parts", None) or []:
            fr = getattr(part, "function_response", None)
            if fr and getattr(fr, "name", None) == "ask_choice" and getattr(fr, "id", None):
                answered.add(fr.id)
            fc = getattr(part, "function_call", None)
            if fc and getattr(fc, "name", None) == "ask_choice" and getattr(fc, "id", None):
                pending = {
                    "function_call_id": fc.id,
                    "invocation_id": getattr(event, "invocation_id", None),
                    "args": dict(fc.args or {}),
                }
    if pending and pending["function_call_id"] not in answered:
        # Also respect long_running_tool_ids when present
        return pending
    if pending and pending["function_call_id"] not in answered:
        return pending
    # Re-scan with long_running preference
    for event in reversed(list(events)):
        long_ids = getattr(event, "long_running_tool_ids", None) or set()
        for part in getattr(getattr(event, "content", None), "parts", None) or []:
            fc = getattr(part, "function_call", None)
            if (
                fc
                and getattr(fc, "name", None) == "ask_choice"
                and fc.id
                and (not long_ids or fc.id in long_ids)
                and fc.id not in answered
            ):
                return {
                    "function_call_id": fc.id,
                    "invocation_id": getattr(event, "invocation_id", None),
                    "args": dict(fc.args or {}),
                }
    return None


def preview_events(events: list[Any], limit: int = 5) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for event in events[-limit:]:
        parts_out: list[dict[str, Any]] = []
        for part in getattr(getattr(event, "content", None), "parts", None) or []:
            entry: dict[str, Any] = {}
            if getattr(part, "text", None):
                entry["text"] = part.text
            fc = getattr(part, "function_call", None)
            if fc:
                entry["functionCall"] = {"name": fc.name, "id": fc.id}
            fr = getattr(part, "function_response", None)
            if fr:
                entry["functionResponse"] = {"name": fr.name, "id": fr.id}
            if entry:
                parts_out.append(entry)
        preview.append({"author": getattr(event, "author", None), "parts": parts_out})
    return preview
