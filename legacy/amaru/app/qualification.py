"""Amaru-specific qualification policy (orchestrator delegates to common)."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from chatty_agent_common import qualification as common_qualification
from chatty_agent_common.qualification import (
    QualificationPolicy,
    parse_bant_signals,
)
from chatty_agent_common.qualification import (
    apply_bant_signals as _apply_bant_signals,
)
from chatty_agent_common.qualification import (
    maybe_execute_handoff as _maybe_execute_handoff,
)

HANDOFF_THRESHOLD = 70
HANDOFF_SOURCE = "amaru_tools"
DEFAULT_BRIDGE = (
    "Un momento, te estoy conectando con un asesor del equipo. "
    "Pronto se pondrán en contacto contigo."
)

REASON_HUMAN = "Cliente solicitó atención humana."
REASON_DISABILITY = "Consulta por discapacidad o accesibilidad."
REASON_CUSTOM_GROUP = "Quiere armar grupo o fecha a medida."
REASON_PLAN_DATE = "Plan y fecha confirmados para reserva."

_POLICY = QualificationPolicy(
    threshold=HANDOFF_THRESHOLD,
    handoff_source=HANDOFF_SOURCE,
    default_bridge=DEFAULT_BRIDGE,
)

__all__ = [
    "DEFAULT_BRIDGE",
    "HANDOFF_SOURCE",
    "HANDOFF_THRESHOLD",
    "REASON_CUSTOM_GROUP",
    "REASON_DISABILITY",
    "REASON_HUMAN",
    "REASON_PLAN_DATE",
    "amaru_gate_qualifies",
    "apply_bant_signals",
    "handoff_reason",
    "maybe_execute_handoff",
    "parse_bant_signals",
    "should_bypass_turn_gate",
]


def amaru_gate_qualifies(criteria: Mapping[str, Any]) -> bool:
    """True when one of the four Amaru paths is open. Score ≥ 70 does not qualify."""
    if criteria.get("explicit_human_request") or criteria.get(
        "disability_access_inquiry"
    ):
        return True
    if str(criteria.get("budget_status") or "") == "Insufficient":
        return False
    return bool(
        criteria.get("plan_and_date_confirmed") or criteria.get("custom_group_accepted")
    )


def should_bypass_turn_gate(criteria: Mapping[str, Any]) -> bool:
    """Turn-1 bypass for explicit human request or disability/accessibility."""
    return bool(
        criteria.get("explicit_human_request")
        or criteria.get("disability_access_inquiry")
    )


def handoff_reason(criteria: Mapping[str, Any]) -> str:
    """Canonical operator reason. Priority: human → disability → group → plan+date."""
    if criteria.get("explicit_human_request"):
        return REASON_HUMAN
    if criteria.get("disability_access_inquiry"):
        return REASON_DISABILITY
    if criteria.get("custom_group_accepted"):
        return REASON_CUSTOM_GROUP
    if criteria.get("plan_and_date_confirmed"):
        return REASON_PLAN_DATE
    return "Lead calificado para atención humana."


def apply_bant_signals(
    *,
    state: MutableMapping[str, Any],
    conversation_id: str | None,
    criteria: Mapping[str, Any],
) -> dict[str, Any]:
    result = _apply_bant_signals(
        state=state,
        conversation_id=None,
        criteria=criteria,
        policy=_POLICY,
        bant_state_key=None,
    )
    parsed = parse_bant_signals(criteria)
    qualifies = amaru_gate_qualifies(parsed) if parsed is not None else False
    result["qualifies"] = qualifies
    state["lead_qualifies"] = "true" if qualifies else "false"
    if conversation_id and parsed is not None:
        common_qualification.persist_conversation_qualification_snapshot(
            conversation_id,
            int(result["score"]),
            parsed,
            qualifies,
        )
    return result


def maybe_execute_handoff(
    *,
    state: MutableMapping[str, Any],
    conversation_id: str | None,
    reason: str,
    qualifies: bool,
    score: int,
    explicit_human_request: bool,
) -> dict[str, Any]:
    return _maybe_execute_handoff(
        state=state,
        conversation_id=conversation_id,
        reason=reason,
        qualifies=qualifies,
        score=score,
        explicit_human_request=explicit_human_request,
        policy=_POLICY,
    )
