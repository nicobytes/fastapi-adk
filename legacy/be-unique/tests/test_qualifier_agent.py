"""Qualifier sub-agent instruction bundle."""

from app.subagents.qualifier.agent import BantSignals, qualifier_agent


def test_qualifier_has_six_bant_fields() -> None:
    fields = set(BantSignals.model_fields.keys())
    assert fields == {
        "interest_level",
        "budget_status",
        "purchase_urgency",
        "has_decision_authority",
        "explicit_human_request",
        "plan_and_date_confirmed",
    }


def test_qualifier_instruction_does_not_include_bridge_example() -> None:
    static = qualifier_agent.static_instruction or ""
    assert "ejemplo de respuesta tras handoff" not in static.lower()
    assert "request_human_handoff" not in static.lower()
