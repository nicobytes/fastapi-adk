"""Be Unique qualification policy (orchestrator delegates to common)."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

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
HANDOFF_SOURCE = "be-unique_tools"
DEFAULT_BRIDGE = (
    "Un momento, le estoy conectando con un asesor del equipo. "
    "Pronto se pondrán en contacto con usted."
)

_POLICY = QualificationPolicy(
    threshold=HANDOFF_THRESHOLD,
    handoff_source=HANDOFF_SOURCE,
    default_bridge=DEFAULT_BRIDGE,
    allow_score_handoff=False,
    score_plan_and_date_confirmed=False,
)

__all__ = [
    "DEFAULT_BRIDGE",
    "HANDOFF_SOURCE",
    "HANDOFF_THRESHOLD",
    "apply_bant_signals",
    "maybe_execute_handoff",
    "parse_bant_signals",
]


def apply_bant_signals(
    *,
    state: MutableMapping[str, Any],
    conversation_id: str | None,
    criteria: Mapping[str, Any],
) -> dict[str, Any]:
    return _apply_bant_signals(
        state=state,
        conversation_id=conversation_id,
        criteria=criteria,
        policy=_POLICY,
        bant_state_key=None,
    )


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
