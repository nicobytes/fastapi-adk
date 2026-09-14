"""Unit tests for BANT scoring + handoff helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from app.qualification import (
    DEFAULT_BRIDGE,
    HANDOFF_SOURCE,
    apply_bant_signals,
    maybe_execute_handoff,
)

_HIGH_ALIGNED = {
    "interest_level": "High",
    "budget_status": "Aligned",
    "purchase_urgency": "ShortTerm",
    "has_decision_authority": True,
    "explicit_human_request": False,
    "plan_and_date_confirmed": False,
}


def test_apply_bant_signals_scores_and_writes_state() -> None:
    state: dict[str, Any] = {"bant_result": _HIGH_ALIGNED.copy()}
    with patch(
        "chatty_agent_common.qualification.persist_conversation_qualification_snapshot"
    ) as persist:
        result = apply_bant_signals(
            state=state,
            conversation_id="conv-test-1",
            criteria=_HIGH_ALIGNED,
        )

    assert result["status"] == "ok"
    assert result["score"] == 90
    assert result["qualifies"] is False
    assert result["explicit_human_request"] is False
    assert state["lead_qualifies"] == "false"
    assert state["qualification_score"] == "90"
    assert state["bant_result"] == _HIGH_ALIGNED
    persist.assert_called_once_with("conv-test-1", 90, _HIGH_ALIGNED, False)


def test_apply_bant_signals_plan_and_date_fast_track() -> None:
    criteria = {
        **_HIGH_ALIGNED,
        "budget_status": "NotMentioned",
        "has_decision_authority": False,
        "plan_and_date_confirmed": True,
    }
    state: dict[str, Any] = {"bant_result": criteria.copy()}
    with patch(
        "chatty_agent_common.qualification.persist_conversation_qualification_snapshot"
    ):
        result = apply_bant_signals(
            state=state,
            conversation_id="conv-test-1",
            criteria=criteria,
        )

    assert result["score"] == 100
    assert result["qualifies"] is True
    assert result["breakdown"]["fast_track"]["reason"] == "plan_and_date_confirmed"


def test_maybe_execute_handoff_rejected_too_early() -> None:
    state: dict[str, Any] = {"user_turn_count": 1}
    result = maybe_execute_handoff(
        state=state,
        conversation_id="conv-test-1",
        reason="Lead alto",
        qualifies=True,
        score=90,
        explicit_human_request=False,
    )
    assert result["status"] == "rejected"
    assert state.get("handoff_phase") != "just_handed_off"


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
        ) as resolve,
    ):
        handoff.return_value = {"status": "success"}
        result = maybe_execute_handoff(
            state=state,
            conversation_id="conv-test-1",
            reason="Reserva confirmada",
            qualifies=True,
            score=100,
            explicit_human_request=False,
        )

    assert result["status"] == "WAITING_HUMAN"
    assert result["bridge_message"] == crm_bridge
    assert state["handoff_phase"] == "just_handed_off"
    assert state["handoff_bridge_message"] == crm_bridge
    handoff.assert_called_once()
    assert handoff.call_args.kwargs["source"] == HANDOFF_SOURCE
    resolve.assert_called_once_with("conv-test-1", default=DEFAULT_BRIDGE)


def test_apply_bant_signals_custom_group_qualifies() -> None:
    criteria = {**_HIGH_ALIGNED, "custom_group_accepted": True}
    state: dict[str, Any] = {"bant_result": criteria.copy()}
    with patch(
        "chatty_agent_common.qualification.persist_conversation_qualification_snapshot"
    ) as persist:
        result = apply_bant_signals(
            state=state,
            conversation_id="conv-test-1",
            criteria=criteria,
        )

    assert result["qualifies"] is True
    assert state["lead_qualifies"] == "true"
    persist.assert_called_once()
    assert persist.call_args.args[3] is True


def test_apply_bant_signals_insufficient_blocks_plan_and_date() -> None:
    criteria = {
        **_HIGH_ALIGNED,
        "budget_status": "Insufficient",
        "plan_and_date_confirmed": True,
    }
    state: dict[str, Any] = {"bant_result": criteria.copy()}
    with patch(
        "chatty_agent_common.qualification.persist_conversation_qualification_snapshot"
    ) as persist:
        result = apply_bant_signals(
            state=state,
            conversation_id="conv-test-1",
            criteria=criteria,
        )

    assert result["qualifies"] is False
    assert state["lead_qualifies"] == "false"
    persist.assert_called_once()
    assert persist.call_args.args[3] is False


def test_maybe_execute_handoff_allows_explicit_human_on_turn1() -> None:
    state: dict[str, Any] = {"user_turn_count": 1}
    with (
        patch(
            "chatty_agent_common.qualification.execute_conversation_handoff"
        ) as handoff,
        patch(
            "chatty_agent_common.qualification.resolve_handoff_bridge_message",
            return_value="bridge",
        ),
    ):
        handoff.return_value = {"status": "success"}
        result = maybe_execute_handoff(
            state=state,
            conversation_id="conv-test-1",
            reason="Cliente pidió asesora",
            qualifies=False,
            score=0,
            explicit_human_request=True,
        )

    assert result["status"] == "WAITING_HUMAN"
    assert result["score"] == 100
    assert state["qualification_score"] == "100"
    handoff.assert_called_once()
    assert handoff.call_args.args[1] == 100
