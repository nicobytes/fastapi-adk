from __future__ import annotations

from typing import Any

from chatty_agent_common.providers.supabase import (
    get_organization_slug,
    search_knowledge,
)

_EMPTY_RESULT = {
    "content": (
        "No relevant results found for this query in the organization's knowledge base."
    ),
    "artifact": [],
}


def run_knowledge_search(
    *,
    organization_slug: str,
    query: str,
    match_count: int,
    full_text_weight: float | None = None,
    semantic_weight: float | None = None,
    rrf_k: int | None = None,
) -> dict[str, Any]:
    """Tenant-scoped hybrid knowledge retrieval for ADK tools.

    Args:
        organization_slug: ``organizations.slug`` for the tenant (never hardcoded).
        query: User/search text.
        match_count: Max fragments to return (clamped to 1-20).
    """
    cleaned_slug = (organization_slug or "").strip()
    if not cleaned_slug:
        raise ValueError("organization_slug cannot be empty")

    cleaned_query = (query or "").strip()
    if not cleaned_query:
        raise ValueError("Query cannot be empty")

    bounded_count = max(1, min(int(match_count), 20))
    organization_id = get_organization_slug(cleaned_slug)
    try:
        rows = search_knowledge(
            organization_id=organization_id,
            query=cleaned_query,
            search_type="hybrid",
            match_count=bounded_count,
            full_text_weight=full_text_weight,
            semantic_weight=semantic_weight,
            rrf_k=rrf_k,
        )
    except RuntimeError:
        return dict(_EMPTY_RESULT)

    if not rows:
        return dict(_EMPTY_RESULT)

    serialized_rows: list[str] = []
    artifact: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        metadata = row.get("metadata")
        content = str(row.get("content", ""))
        serialized_rows.append(f"Result {index}\nContent: {content}")
        artifact.append(
            {
                "id": row.get("id"),
                "content": content,
                "metadata": metadata if isinstance(metadata, dict) else {},
            }
        )

    return {"content": "\n\n".join(serialized_rows), "artifact": artifact}
