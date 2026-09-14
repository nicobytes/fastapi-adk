from __future__ import annotations

import logging
from typing import Any, Literal

import httpx
from postgrest.exceptions import APIError
from supabase import Client, ClientOptions, create_client

from chatty_agent_common.utils import require_env

logger = logging.getLogger(__name__)

_SUPABASE_CLIENT: Client | None = None
_DEFAULT_FUNCTION_CLIENT_TIMEOUT_SECONDS = 60

_CONNECT_ERROR_HINT = (
    "Cannot connect to Supabase (check SUPABASE_URL). If you run the agent on your "
    "machine, use the local API URL from `supabase status` (typically "
    "http://127.0.0.1:54321). Hostnames like api.supabase.internal only resolve "
    "inside Docker/the same private network."
)


def get_supabase_client() -> Client:
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is None:
        supabase_url = require_env("SUPABASE_URL")
        supabase_secret_key = require_env("SUPABASE_SECRET_KEY")
        _SUPABASE_CLIENT = create_client(
            supabase_url,
            supabase_secret_key,
            options=ClientOptions(
                # supabase-py defaults to 5s; hybrid search-knowledge often exceeds that.
                function_client_timeout=_DEFAULT_FUNCTION_CLIENT_TIMEOUT_SECONDS,
            ),
        )
    return _SUPABASE_CLIENT


def get_organization_slug(slug: str) -> str:
    client = get_supabase_client()
    try:
        response = (
            client.table("organizations")
            .select("id")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc
    data = response.data
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"No organization found for slug={slug}")
    first_row = data[0]
    if not isinstance(first_row, dict):
        raise RuntimeError("Organization query returned an invalid row shape")
    org_id = first_row.get("id")
    if not isinstance(org_id, str) or not org_id:
        raise RuntimeError("Organization query returned an invalid id")
    return org_id


ConversationStatus = Literal[
    "AI_AUTO",
    "AI_HELPER",
    "WAITING_HUMAN",
    "HUMAN_ACTIVE",
    "CLOSED",
]

ConversationStage = Literal[
    "first_contact",
    "in_conversation",
    "handed_off",
]

SearchKnowledgeType = Literal["hybrid"]


def _missing_conversation_error(conversation_id: str) -> RuntimeError:
    return RuntimeError(
        f"No conversation updated for id={conversation_id} (missing row or invalid id)"
    )


def _is_conversation_not_found_api_error(exc: APIError) -> bool:
    message = str(getattr(exc, "message", "") or exc).lower()
    details = str(getattr(exc, "details", "") or "").lower()
    blob = f"{message} {details}"
    return "not found" in blob and "conversation" in blob


def _patch_conversation_agent_state(
    conversation_id: str,
    *,
    metadata_patch: dict[str, Any] | None = None,
    status: ConversationStatus | None = None,
    qualification_score: int | None = None,
    handoff_reason: str | None = None,
    stage: ConversationStage | None = None,
) -> dict[str, Any]:
    """Merge ``metadata_patch`` via RPC ``metadata || patch`` (atomic nested keys)."""
    if not conversation_id or not conversation_id.strip():
        raise ValueError("conversation_id cannot be empty")

    cleaned_id = conversation_id.strip()
    params: dict[str, Any] = {"p_conversation_id": cleaned_id}
    if metadata_patch is not None:
        params["p_metadata_patch"] = metadata_patch
    if status is not None:
        params["p_status"] = status
    if qualification_score is not None:
        params["p_qualification_score"] = max(0, min(int(qualification_score), 100))
    if handoff_reason is not None:
        cleaned_reason = handoff_reason.strip()
        if cleaned_reason:
            params["p_handoff_reason"] = cleaned_reason
    if stage is not None:
        params["p_stage"] = stage

    client = get_supabase_client()
    try:
        response = client.rpc("patch_conversation_agent_state", params).execute()
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc
    except APIError as exc:
        if _is_conversation_not_found_api_error(exc):
            raise _missing_conversation_error(cleaned_id) from exc
        raise RuntimeError(
            f"Conversation patch failed for id={cleaned_id}: {exc}"
        ) from exc

    data = response.data
    if isinstance(data, list):
        if not data:
            raise _missing_conversation_error(cleaned_id)
        first_row = data[0]
    else:
        first_row = data
    if not isinstance(first_row, dict):
        raise RuntimeError("Conversation patch returned an invalid row shape")
    return first_row


def update_conversation_status(
    conversation_id: str,
    status: ConversationStatus,
    metadata_patch: dict[str, Any] | None = None,
    qualification_score: int | None = None,
    handoff_reason: str | None = None,
    stage: ConversationStage | None = None,
) -> dict[str, Any]:
    """Update conversation fields; merge ``metadata_patch`` into JSONB atomically."""
    return _patch_conversation_agent_state(
        conversation_id,
        metadata_patch=metadata_patch,
        status=status,
        qualification_score=qualification_score,
        handoff_reason=handoff_reason,
        stage=stage,
    )


def update_conversation_qualification_score(
    conversation_id: str,
    qualification_score: int,
    metadata_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist ``qualification_score`` (0-100) and optional metadata patch atomically."""
    return _patch_conversation_agent_state(
        conversation_id,
        metadata_patch=metadata_patch,
        qualification_score=qualification_score,
    )


def fetch_handoff_bridge_message(conversation_id: str) -> str | None:
    """Load ``ai_agents.handoff_bridge_message`` for a conversation's inbox agent.

    Path: ``conversations`` → ``inboxes`` → ``ai_agents``. Returns a trimmed
    non-empty string, or ``None`` when missing/blank/unreadable. Best-effort:
    connection or shape errors are logged and yield ``None`` so callers can
    fall back to env/default without blocking handoff.
    """
    if not conversation_id or not conversation_id.strip():
        return None

    client = get_supabase_client()
    try:
        response = (
            client.table("conversations")
            .select("inboxes(ai_agents(handoff_bridge_message))")
            .eq("id", conversation_id.strip())
            .limit(1)
            .execute()
        )
    except httpx.ConnectError:
        logger.warning(
            "Could not fetch handoff_bridge_message for conversation %s: %s",
            conversation_id,
            _CONNECT_ERROR_HINT,
        )
        return None
    except Exception:
        logger.exception(
            "Unexpected error fetching handoff_bridge_message for conversation %s",
            conversation_id,
        )
        return None

    data = response.data
    if not isinstance(data, list) or not data:
        return None
    row = data[0]
    if not isinstance(row, dict):
        return None

    inbox = row.get("inboxes")
    if isinstance(inbox, list):
        inbox = inbox[0] if inbox else None
    if not isinstance(inbox, dict):
        return None

    agent = inbox.get("ai_agents")
    if isinstance(agent, list):
        agent = agent[0] if agent else None
    if not isinstance(agent, dict):
        return None

    message = agent.get("handoff_bridge_message")
    if not isinstance(message, str):
        return None
    cleaned = message.strip()
    return cleaned or None


def search_knowledge(
    organization_id: str,
    query: str,
    search_type: SearchKnowledgeType = "hybrid",
    match_count: int = 8,
    *,
    full_text_weight: float | None = None,
    semantic_weight: float | None = None,
    rrf_k: int | None = None,
) -> list[dict[str, Any]]:
    """Tenant-scoped knowledge search via the `search-knowledge` Edge Function."""
    client = get_supabase_client()
    body: dict[str, Any] = {
        "organizationId": organization_id,
        "searchType": search_type,
        "query": query,
        "matchCount": match_count,
    }
    if full_text_weight is not None:
        body["fullTextWeight"] = full_text_weight
    if semantic_weight is not None:
        body["semanticWeight"] = semantic_weight
    if rrf_k is not None:
        body["rrfK"] = rrf_k
    try:
        raw = client.functions.invoke(
            "search-knowledge",
            invoke_options={
                "body": body,
                "responseType": "json",
            },
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc
    except httpx.ReadTimeout as exc:
        raise RuntimeError(
            "search-knowledge timed out; try again or narrow the query."
        ) from exc
    if not isinstance(raw, dict):
        raise RuntimeError("search-knowledge returned a non-object payload")
    if raw.get("error"):
        raise RuntimeError(str(raw["error"]))
    results = raw.get("results")
    if not isinstance(results, list):
        raise RuntimeError("search-knowledge returned an invalid results payload")
    rows: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            raise RuntimeError("search-knowledge returned an invalid row shape")
        rows.append(row)
    return rows
