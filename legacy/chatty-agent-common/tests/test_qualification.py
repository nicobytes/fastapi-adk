"""Tests for shared BANT qualification helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from chatty_agent_common.qualification import (
    QualificationPolicy,
    apply_bant_signals,
    maybe_execute_handoff,
    parse_bant_signals,
)

_HIGH_ALIGNED = {
    "interest_level": "High",
    "budget_status": "Aligned",
    "purchase_urgency": "ShortTerm",
    "has_decision_authority": True,
    "explicit_human_request": False,
    "plan_and_date_confirmed": False,
}

_POLICY = QualificationPolicy(
    threshold=70,
    handoff_source="test_tools",
    default_bridge="default bridge",
)


def test_parse_bant_signals_accepts_json_string() -> None:
    import json

    parsed = parse_bant_signals(json.dumps(_HIGH_ALIGNED))
    assert parsed == _HIGH_ALIGNED


def test_parse_bant_signals_six_fields_without_extras() -> None:
    parsed = parse_bant_signals(_HIGH_ALIGNED)
    assert parsed is not None
    assert parsed == _HIGH_ALIGNED
    assert "custom_group_accepted" not in parsed
    assert "disability_access_inquiry" not in parsed


def test_parse_bant_signals_copies_optional_extras() -> None:
    raw = {
        **_HIGH_ALIGNED,
        "custom_group_accepted": True,
        "disability_access_inquiry": True,
    }
    parsed = parse_bant_signals(raw)
    assert parsed is not None
    assert parsed["custom_group_accepted"] is True
    assert parsed["disability_access_inquiry"] is True


def test_parse_bant_signals_missing_required_field_returns_none() -> None:
    assert parse_bant_signals({"interest_level": "High"}) is None


def test_apply_bant_signals_scores_and_writes_state() -> None:
    state: dict[str, Any] = {}
    with patch(
        "chatty_agent_common.qualification.persist_conversation_qualification_snapshot"
    ) as persist:
        result = apply_bant_signals(
            state=state,
            conversation_id="conv-test-1",
            criteria=_HIGH_ALIGNED,
            policy=_POLICY,
        )

    assert result["status"] == "ok"
    assert result["score"] == 90
    assert result["qualifies"] is True
    assert state["lead_qualifies"] == "true"
    assert state["qualification_score"] == "90"
    persist.assert_called_once_with("conv-test-1", 90, _HIGH_ALIGNED, True)


def test_apply_bant_signals_respects_custom_threshold() -> None:
    state: dict[str, Any] = {}
    strict_policy = QualificationPolicy(
        threshold=95,
        handoff_source="test_tools",
        default_bridge="default bridge",
    )
    with patch(
        "chatty_agent_common.qualification.persist_conversation_qualification_snapshot"
    ):
        result = apply_bant_signals(
            state=state,
            conversation_id="conv-test-1",
            criteria=_HIGH_ALIGNED,
            policy=strict_policy,
        )

    assert result["score"] == 90
    assert result["qualifies"] is False


def test_maybe_execute_handoff_rejected_too_early() -> None:
    state: dict[str, Any] = {"user_turn_count": 1}
    result = maybe_execute_handoff(
        state=state,
        conversation_id="conv-test-1",
        reason="Lead alto",
        qualifies=True,
        score=90,
        explicit_human_request=False,
        policy=_POLICY,
    )
    assert result["status"] == "rejected"


def test_maybe_execute_handoff_success_sets_bridge() -> None:
    state: dict[str, Any] = {"user_turn_count": 2}
    crm_bridge = "¡Perfecto! Voy a enviar tu solicitud a Laura."
    with (
        patch(
            "chatty_agent_common.qualification.execute_conversation_handoff"
        ) as handoff,
        patch(
            "chatty_agent_common.qualification.resolve_handoff_bridge_message",
            return_value=crm_bridge,
        ),
    ):
        handoff.return_value = {"status": "success"}
        result = maybe_execute_handoff(
            state=state,
            conversation_id="conv-test-1",
            reason="Reserva confirmada",
            qualifies=True,
            score=100,
            explicit_human_request=False,
            policy=_POLICY,
        )

    assert result["status"] == "WAITING_HUMAN"
    assert result["bridge_message"] == crm_bridge
    assert state["handoff_phase"] == "just_handed_off"
    handoff.assert_called_once()
    assert handoff.call_args.kwargs["source"] == "test_tools"
