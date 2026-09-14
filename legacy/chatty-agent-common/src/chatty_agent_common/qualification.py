"""Shared BANT parsing, scoring persistence, and HITL handoff helpers."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from chatty_agent_common.handoff import (
    execute_conversation_handoff,
    persist_conversation_qualification_snapshot,
    resolve_handoff_bridge_message,
)
from chatty_agent_common.lead_scoring import HANDOFF_THRESHOLD, calculate_lead_score

logger = logging.getLogger(__name__)

TURN_COUNT_KEY = "user_turn_count"
DEFAULT_MIN_TURNS_FOR_HANDOFF = 2

BANT_FIELDS = (
    "interest_level",
    "budget_status",
    "purchase_urgency",
    "has_decision_authority",
    "explicit_human_request",
    "plan_and_date_confirmed",
)

# Amaru-only extras. Not required; absent ≡ false. Do not add to BANT_FIELDS.
OPTIONAL_BANT_BOOL_FIELDS = (
    "custom_group_accepted",
    "disability_access_inquiry",
)


@dataclass(frozen=True)
class QualificationPolicy:
    """Per-agent qualification and handoff settings."""

    handoff_source: str
    default_bridge: str
    threshold: int = HANDOFF_THRESHOLD
    min_turns_for_handoff: int | None = DEFAULT_MIN_TURNS_FOR_HANDOFF
    allow_score_handoff: bool = True
    score_plan_and_date_confirmed: bool = True


def parse_bant_signals(raw: Any) -> dict[str, Any] | None:
    """Normalize qualifier or tool output into scoring criteria."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, Mapping):
        return None
    criteria: dict[str, Any] = {}
    for key in BANT_FIELDS:
        if key not in raw:
            return None
        criteria[key] = raw[key]
    for key in OPTIONAL_BANT_BOOL_FIELDS:
        if key in raw:
            criteria[key] = bool(raw[key])
    return criteria


def apply_bant_signals(
    *,
    state: MutableMapping[str, Any],
    conversation_id: str | None,
    criteria: Mapping[str, Any],
    policy: QualificationPolicy,
    bant_state_key: str | None = "bant_result",
) -> dict[str, Any]:
    """Score BANT criteria, persist score, and write derived session flags."""
    parsed = parse_bant_signals(criteria)
    if parsed is None:
        raise ValueError("Invalid BANT criteria")

    plan_for_scoring = (
        bool(parsed["plan_and_date_confirmed"])
        if policy.score_plan_and_date_confirmed
        else False
    )
    result = calculate_lead_score(
        interest_level=parsed["interest_level"],  # type: ignore[arg-type]
        budget_status=parsed["budget_status"],  # type: ignore[arg-type]
        purchase_urgency=parsed["purchase_urgency"],  # type: ignore[arg-type]
        has_decision_authority=bool(parsed["has_decision_authority"]),
        explicit_human_request=bool(parsed["explicit_human_request"]),
        plan_and_date_confirmed=plan_for_scoring,
        threshold=policy.threshold,
    )
    score = int(result["score"])
    qualifies = bool(result["qualifies"])

    if bant_state_key is not None:
        state[bant_state_key] = dict(parsed)
    state["qualification_score"] = str(score)
    state["lead_qualifies"] = "true" if qualifies else "false"
    state["explicit_human_request"] = (
        "true" if parsed["explicit_human_request"] else "false"
    )

    if conversation_id:
        persist_conversation_qualification_snapshot(
            conversation_id,
            score,
            parsed,
            qualifies,
        )

    return {
        "status": "ok",
        "score": score,
        "qualifies": qualifies,
        "explicit_human_request": bool(parsed["explicit_human_request"]),
        "threshold": policy.threshold,
        "breakdown": result.get("breakdown", {}),
    }


def maybe_execute_handoff(
    *,
    state: MutableMapping[str, Any],
    conversation_id: str | None,
    reason: str,
    qualifies: bool,
    score: int,
    explicit_human_request: bool,
    policy: QualificationPolicy,
) -> dict[str, Any]:
    """Apply turn gating and execute HITL when policy allows."""
    cleaned_reason = (reason or "").strip()
    if not cleaned_reason:
        cleaned_reason = "Lead calificado para atención humana."

    turn_count = int(state.get(TURN_COUNT_KEY, 0) or 0)
    may_handoff_on_score = policy.allow_score_handoff and qualifies

    if not may_handoff_on_score and not explicit_human_request:
        return {
            "status": "rejected",
            "message": "El lead aún no califica para handoff.",
        }

    if (
        policy.min_turns_for_handoff is not None
        and turn_count < policy.min_turns_for_handoff
        and not explicit_human_request
    ):
        return {
            "status": "rejected",
            "message": "Demasiado pronto para derivar (primer mensaje).",
        }

    if not conversation_id:
        return {
            "status": "error",
            "message": "No hay conversation_id en la sesión; no se pudo derivar.",
        }

    effective_score = score if score > 0 else (100 if explicit_human_request else score)
    bridge = resolve_handoff_bridge_message(
        conversation_id,
        default=policy.default_bridge,
    )
    try:
        execute_conversation_handoff(
            conversation_id,
            effective_score,
            cleaned_reason[:200],
            source=policy.handoff_source,
        )
    except Exception:
        logger.exception("maybe_execute_handoff failed for %s", conversation_id)
        return {
            "status": "error",
            "message": "No se pudo completar el handoff.",
        }

    state["handoff_phase"] = "just_handed_off"
    state["handoff_bridge_message"] = bridge
    state["qualification_score"] = str(effective_score)

    return {
        "status": "WAITING_HUMAN",
        "bridge_message": bridge,
        "score": effective_score,
        "reason": cleaned_reason[:200],
    }
