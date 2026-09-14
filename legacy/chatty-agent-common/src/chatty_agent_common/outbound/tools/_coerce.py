"""Coerce Gemini-stringified nested args into mappings."""

from __future__ import annotations

import json
import re
from typing import Any

from chatty_agent_common.outbound.models import MAX_BUTTON_TITLE_LENGTH


def coerce_mapping(value: Any) -> Any:
    """Accept dicts or JSON object strings (Gemini sometimes stringifies nested args)."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        if isinstance(parsed, dict):
            return parsed
        return value
    return value


def _slug_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return (slug or "option")[:256]


def coerce_reply_button(value: Any) -> dict[str, str]:
    """Normalize a button arg into ``{id, title}``.

    Gemini may pass:
    - ``{"id": "...", "title": "..."}``
    - a JSON object string of that shape
    - a bare title string (e.g. ``"Sucre"``) — derive a stable slug id
    """
    mapped = coerce_mapping(value)
    if isinstance(mapped, dict):
        button_id = mapped.get("id")
        title = mapped.get("title")
        if isinstance(title, str) and title.strip():
            title = title.strip()[:MAX_BUTTON_TITLE_LENGTH]
            if isinstance(button_id, str) and button_id.strip():
                return {"id": button_id.strip()[:256], "title": title}
            return {"id": _slug_id(title), "title": title}
        if isinstance(button_id, str) and button_id.strip() and not title:
            # id-only — use id as visible title (truncated)
            button_id = button_id.strip()[:256]
            return {"id": button_id, "title": button_id[:MAX_BUTTON_TITLE_LENGTH]}

    if isinstance(value, str) and value.strip():
        title = value.strip()[:MAX_BUTTON_TITLE_LENGTH]
        return {"id": _slug_id(title), "title": title}

    raise ValueError(
        "Each button needs id+title (dict/JSON) or a non-empty title string; "
        f"got {type(value).__name__}: {value!r}"
    )
