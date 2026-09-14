"""Bridge ADK playground sessions to local Supabase conversations.

When ``ADK_DEV_MODE=true`` and ``SUPABASE_URL`` points at localhost, ensure a
``conversations`` row exists with ``id = session.id`` so tools that pass the
ADK session id as ``conversationId`` (booking, handoff, scoring) hit real rows
without going through Nest/WhatsApp.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import httpx
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from chatty_agent_common.outbound.playground import is_adk_dev_mode
from chatty_agent_common.providers.supabase import (
    get_organization_slug,
    get_supabase_client,
)

_CONNECT_ERROR_HINT = (
    "Cannot connect to Supabase (check SUPABASE_URL). Playground bridge "
    "requires local Supabase (typically http://127.0.0.1:54321)."
)

logger = logging.getLogger(__name__)

PLAYGROUND_SOURCE = "adk_playground"
PLAYGROUND_READY_STATE_KEY = "_playground_conversation_ready"

__all__ = [
    "PLAYGROUND_READY_STATE_KEY",
    "PLAYGROUND_SOURCE",
    "ensure_playground_conversation",
    "is_local_supabase_url",
    "make_ensure_playground_conversation_callback",
    "playground_conversation_id",
]


def is_local_supabase_url(url: str | None = None) -> bool:
    """True when SUPABASE_URL host is localhost / 127.0.0.1 / ::1."""
    raw = (url if url is not None else os.getenv("SUPABASE_URL", "")).strip()
    if not raw:
        return False
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _normalize_uuid(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return str(uuid.UUID(cleaned))
    except ValueError:
        return None


def _resolve_inbox_id(organization_id: str) -> str:
    override = os.getenv("ADK_DEV_INBOX_ID", "").strip()
    if override:
        inbox_id = _normalize_uuid(override)
        if inbox_id is None:
            raise RuntimeError(f"ADK_DEV_INBOX_ID is not a valid UUID: {override!r}")
        return inbox_id

    client = get_supabase_client()
    try:
        response = (
            client.table("inboxes")
            .select("id")
            .eq("organization_id", organization_id)
            .eq("channel_type", "whatsapp")
            .eq("is_active", True)
            .order("created_at")
            .limit(1)
            .execute()
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc

    data = response.data
    if not isinstance(data, list) or not data:
        raise RuntimeError(
            f"No active WhatsApp inbox for organization_id={organization_id}. "
            "Seed local Supabase (just db-reset) or set ADK_DEV_INBOX_ID."
        )
    row = data[0]
    if not isinstance(row, dict):
        raise RuntimeError("Inbox query returned an invalid row shape")
    inbox_id = row.get("id")
    if not isinstance(inbox_id, str) or not inbox_id:
        raise RuntimeError("Inbox query returned an invalid id")
    return inbox_id


def _conversation_exists(conversation_id: str) -> bool:
    client = get_supabase_client()
    try:
        response = (
            client.table("conversations")
            .select("id")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc
    data = response.data
    return isinstance(data, list) and bool(data)


def ensure_playground_conversation(
    session_id: str,
    org_slug: str,
) -> dict[str, Any]:
    """Create customer + conversation for a playground session when allowed.

    Returns a status dict. Never raises for gate skips; raises or returns
    ``status=error`` only when creation fails after gates pass.
    """
    if not is_adk_dev_mode():
        return {"status": "skipped", "reason": "adk_dev_mode_off"}

    if not is_local_supabase_url():
        logger.warning(
            "ADK_DEV_MODE: skipping playground conversation ensure — "
            "SUPABASE_URL is not localhost (refusing remote writes)"
        )
        return {"status": "skipped", "reason": "non_local_supabase"}

    conversation_id = _normalize_uuid(session_id)
    if conversation_id is None:
        return {
            "status": "error",
            "message": f"session_id is not a valid UUID: {session_id!r}",
        }

    cleaned_slug = (org_slug or "").strip()
    if not cleaned_slug:
        return {"status": "error", "message": "org_slug cannot be empty"}

    try:
        if _conversation_exists(conversation_id):
            return {
                "status": "exists",
                "conversation_id": conversation_id,
            }

        organization_id = get_organization_slug(cleaned_slug)
        inbox_id = _resolve_inbox_id(organization_id)
        client = get_supabase_client()

        customer_response = (
            client.table("customers")
            .insert(
                {
                    "organization_id": organization_id,
                    "name": "Playground User",
                    "phone": None,
                    "metadata": {
                        "source": PLAYGROUND_SOURCE,
                        "session_id": conversation_id,
                    },
                }
            )
            .execute()
        )
        customer_rows = customer_response.data
        if not isinstance(customer_rows, list) or not customer_rows:
            raise RuntimeError("Customer insert returned no rows")
        customer_row = customer_rows[0]
        if not isinstance(customer_row, dict):
            raise RuntimeError("Customer insert returned an invalid row shape")
        customer_id = customer_row.get("id")
        if not isinstance(customer_id, str) or not customer_id:
            raise RuntimeError("Customer insert returned an invalid id")

        conversation_response = (
            client.table("conversations")
            .insert(
                {
                    "id": conversation_id,
                    "organization_id": organization_id,
                    "inbox_id": inbox_id,
                    "customer_id": customer_id,
                    "status": "AI_AUTO",
                    "stage": "first_contact",
                    "metadata": {
                        "source": PLAYGROUND_SOURCE,
                        "mock": True,
                    },
                }
            )
            .execute()
        )
        conversation_rows = conversation_response.data
        if not isinstance(conversation_rows, list) or not conversation_rows:
            raise RuntimeError("Conversation insert returned no rows")

        logger.info(
            "ADK_DEV_MODE: ensured playground conversation %s for org=%s",
            conversation_id,
            cleaned_slug,
        )
        return {
            "status": "created",
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "inbox_id": inbox_id,
            "organization_id": organization_id,
        }
    except Exception as exc:
        logger.warning(
            "ADK_DEV_MODE: failed to ensure playground conversation %s: %s",
            session_id,
            exc,
        )
        return {"status": "error", "message": str(exc)}


def playground_conversation_id(tool_context: Any) -> str | None:
    """Return ADK ``session.id`` for Nest when it is safe to send as conversationId.

    In ``ADK_DEV_MODE``, only return the id after playground ensure marked the
    session ready (local Supabase row exists). Otherwise return ``None`` so
    booking omits ``conversationId`` and Nest does not 400 on a missing row
    (e.g. ``just serve-prod`` against cloud).

    Outside ``ADK_DEV_MODE`` (WhatsApp / production), always return ``session.id``.
    """
    session = getattr(tool_context, "session", None)
    session_id = getattr(session, "id", None) if session is not None else None
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    cleaned = session_id.strip()

    if not is_adk_dev_mode():
        return cleaned

    state = getattr(tool_context, "state", None)
    if state is not None and state.get(PLAYGROUND_READY_STATE_KEY):
        return cleaned
    return None


def make_ensure_playground_conversation_callback(
    org_slug: str,
) -> Callable[[CallbackContext], types.Content | None]:
    """``before_agent_callback`` factory: ensure DB row for playground sessions."""

    cleaned_slug = (org_slug or "").strip()

    def ensure_playground_conversation_callback(
        callback_context: CallbackContext,
    ) -> types.Content | None:
        state = callback_context.state
        if state.get(PLAYGROUND_READY_STATE_KEY):
            return None

        if not is_adk_dev_mode():
            return None

        session = getattr(callback_context, "session", None)
        session_id = getattr(session, "id", None) if session is not None else None
        if not isinstance(session_id, str) or not session_id.strip():
            logger.warning(
                "ADK_DEV_MODE: no session.id on callback_context; "
                "skipping playground conversation ensure"
            )
            return None

        result = ensure_playground_conversation(session_id, cleaned_slug)
        status = result.get("status")
        if status in {"created", "exists"}:
            state[PLAYGROUND_READY_STATE_KEY] = True
        elif status == "error":
            logger.warning(
                "ADK_DEV_MODE: playground conversation ensure error: %s",
                result.get("message"),
            )
        return None

    return ensure_playground_conversation_callback
