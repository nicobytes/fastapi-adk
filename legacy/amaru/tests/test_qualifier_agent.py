"""Qualifier sub-agent instruction bundle."""

from app.subagents.qualifier.agent import BantSignals, qualifier_agent


def test_qualifier_bant_fields() -> None:
    fields = set(BantSignals.model_fields.keys())
    assert fields == {
        "interest_level",
        "budget_status",
        "purchase_urgency",
        "has_decision_authority",
        "explicit_human_request",
        "plan_and_date_confirmed",
        "custom_group_accepted",
        "disability_access_inquiry",
    }


def test_qualifier_instruction_does_not_include_bridge_example() -> None:
    static = qualifier_agent.static_instruction or ""
    assert "ejemplo de respuesta tras handoff" not in static.lower()
    assert "request_human_handoff" not in static.lower()


def test_qualifier_instruction_requires_reserve_that_departure() -> None:
    static = (qualifier_agent.static_instruction or "").lower()
    assert "reservar esa" in static
    assert "no lo reutilices" in static or "no reutilices" in static
    assert "custom_group_accepted" in static
    assert "disability_access_inquiry" in static
    assert "sí esa fecha / me queda / dale" in static
    assert "preguntara si quieren reservar" in static
