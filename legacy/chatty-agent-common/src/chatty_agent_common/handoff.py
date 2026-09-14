from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from chatty_agent_common.providers.supabase import (
    fetch_handoff_bridge_message,
    update_conversation_qualification_score,
    update_conversation_status,
)

logger = logging.getLogger(__name__)

_HANDOFF_STATUS = "WAITING_HUMAN"
_MISSING_CONVERSATION_PREFIX = "No conversation updated for id="
_BRIDGE_ENV_VAR = "HANDOFF_BRIDGE_MESSAGE"


def _is_dev_mode() -> bool:
    return os.getenv("ADK_DEV_MODE", "").strip().lower() == "true"


def resolve_handoff_bridge_message(
    conversation_id: str,
    *,
    default: str,
    env_var: str = _BRIDGE_ENV_VAR,
) -> str:
    """Resolve bridge text: CRM DB → env override → tenant default.

    ``ai_agents.handoff_bridge_message`` (via conversation inbox) wins when
    non-empty. ``HANDOFF_BRIDGE_MESSAGE`` supports local/eval overrides. Empty
    CRM + empty env yields ``default`` (agent hardcoded fallback).
    """
    from_db = fetch_handoff_bridge_message(conversation_id)
    if from_db:
        return from_db
    from_env = os.getenv(env_var, "").strip()
    if from_env:
        return from_env
    return default


def _is_missing_conversation_error(exc: RuntimeError) -> bool:
    return str(exc).startswith(_MISSING_CONVERSATION_PREFIX)


def _build_qualification_snapshot(
    criteria: Mapping[str, Any],
    score: int,
    qualifies: bool,
) -> dict[str, Any]:
    """Latest BANT signals plus derived score for ``metadata.qualification``."""
    bounded_score = max(0, min(int(score), 100))
    return {
        **dict(criteria),
        "score": bounded_score,
        "qualifies": bool(qualifies),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def persist_conversation_qualification_snapshot(
    conversation_id: str,
    score: int,
    criteria: Mapping[str, Any],
    qualifies: bool,
) -> None:
    """Best-effort write of score + BANT snapshot into conversation metadata.

    Never raises: missing rows in ADK_DEV_MODE are skipped; other failures are
    logged so customer replies are not blocked by CRM side effects.

    Uses Postgres ``metadata || patch`` so concurrent handoff writes cannot
    erase ``metadata.qualification`` (and vice versa).
    """
    if not conversation_id or not conversation_id.strip():
        return

    bounded_score = max(0, min(int(score), 100))
    conversation_id = conversation_id.strip()
    qualification_snapshot = _build_qualification_snapshot(
        criteria,
        bounded_score,
        qualifies,
    )

    try:
        update_conversation_qualification_score(
            conversation_id=conversation_id,
            qualification_score=bounded_score,
            metadata_patch={"qualification": qualification_snapshot},
        )
    except RuntimeError as exc:
        if _is_dev_mode() and _is_missing_conversation_error(exc):
            logger.warning(
                "Dev mode: conversation %s not found in DB, skipping qualification update",
                conversation_id,
            )
            return
        logger.exception(
            "Failed to persist qualification snapshot for conversation %s",
            conversation_id,
        )
    except Exception:
        logger.exception(
            "Unexpected error persisting qualification snapshot for conversation %s",
            conversation_id,
        )


def execute_conversation_handoff(
    conversation_id: str,
    score: int,
    reason: str,
    *,
    source: str,
) -> dict[str, Any]:
    """Update conversation status to WAITING_HUMAN and persist handoff metadata.

    Does not insert a chat message. The Postgres trigger
    ``util.emit_conversation_lifecycle_events`` (see
    ``projects/supabase/schemas/conversation_timeline.sql``) writes the
    timeline system row (``event_type=conversation.handoff``, ``content=NULL``).

    Metadata uses atomic JSONB merge so an in-flight qualification snapshot is
    preserved under ``metadata.qualification``.

    Args:
        source: Tenant handoff metadata label (e.g. ``amaru_workflow``).
    """
    if not conversation_id or not conversation_id.strip():
        raise ValueError("conversation_id cannot be empty")

    cleaned_reason = (reason or "").strip()
    if not cleaned_reason:
        raise ValueError("reason cannot be empty")

    cleaned_source = (source or "").strip()
    if not cleaned_source:
        raise ValueError("source cannot be empty")

    bounded_score = max(0, min(int(score), 100))
    conversation_id = conversation_id.strip()

    handoff_patch = {
        "handoff": {
            "score": bounded_score,
            "reason": cleaned_reason,
            "requested_at": datetime.now(UTC).isoformat(),
            "source": cleaned_source,
        }
    }

    try:
        row = update_conversation_status(
            conversation_id=conversation_id,
            status=_HANDOFF_STATUS,
            stage="handed_off",
            metadata_patch=handoff_patch,
            qualification_score=bounded_score,
            handoff_reason=cleaned_reason,
        )
    except RuntimeError as exc:
        if _is_dev_mode() and _is_missing_conversation_error(exc):
            logger.warning(
                "Dev mode: conversation %s not found in DB, skipping status update",
                conversation_id,
            )
            return {
                "status": "success",
                "conversation_id": conversation_id,
                "conversation_status": _HANDOFF_STATUS,
                "score": bounded_score,
                "reason": cleaned_reason,
            }
        raise

    return {
        "status": "success",
        "conversation_id": conversation_id,
        "conversation_status": row.get("status", _HANDOFF_STATUS),
        "score": bounded_score,
        "reason": cleaned_reason,
    }
