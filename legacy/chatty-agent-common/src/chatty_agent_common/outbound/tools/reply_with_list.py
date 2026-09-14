"""Pure ADK tool: queue an interactive list outbound intent."""

from __future__ import annotations

from typing import Any

from chatty_agent_common.outbound.models import (
    MAX_LIST_ROWS,
    MAX_LIST_SECTIONS,
    IntentToolResult,
    ListIntent,
    ListRow,
    ListSection,
)
from chatty_agent_common.outbound.tools._coerce import coerce_mapping


def reply_with_list(
    body: str,
    button_label: str,
    sections: list[dict[str, Any] | str],
) -> dict[str, Any]:
    """Queue an interactive list message (sections with rows).

    Use when there are more than 3 options. ``button_label`` is the list CTA
    (max 20 chars). Each section has ``title`` and ``rows`` with ``id``/``title``
    (dict, or a JSON object string when Gemini stringifies nested args).

    WhatsApp allows at most ``MAX_LIST_ROWS`` rows across all sections; extras
    are dropped (first-N kept) so the tool succeeds instead of failing validation.
    """
    remaining = MAX_LIST_ROWS
    parsed_sections: list[ListSection] = []
    for section in sections[:MAX_LIST_SECTIONS]:
        if remaining <= 0:
            break
        section_data = coerce_mapping(section)
        if not isinstance(section_data, dict):
            raise TypeError("each section must be an object with title and rows")
        raw_rows = section_data.get("rows", [])
        if not isinstance(raw_rows, list):
            raise TypeError("section rows must be a list")
        take = raw_rows[:remaining]
        if not take:
            continue
        rows = [ListRow.model_validate(coerce_mapping(r)) for r in take]
        parsed_sections.append(
            ListSection(title=section_data["title"], rows=rows),
        )
        remaining -= len(rows)

    if not parsed_sections:
        raise ValueError("sections must include at least one row")

    intent = ListIntent(
        body=body,
        button_label=button_label,
        sections=parsed_sections,
    )
    return IntentToolResult(intent=intent).to_response_dict()
