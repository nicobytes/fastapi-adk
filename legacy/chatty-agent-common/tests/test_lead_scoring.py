"""Deterministic lead scoring regression tests (Cocuy booking handoff case)."""

from chatty_agent_common.lead_scoring import calculate_lead_score

# Cocuy conversation turn 4: "me intersa quiero agendar"
COCUY_TURN_4 = {
    "interest_level": "High",
    "budget_status": "NotMentioned",
    "purchase_urgency": "Uncertain",
    "has_decision_authority": False,
    "explicit_human_request": False,
    "plan_and_date_confirmed": False,
}

# Cocuy turn 5: "si esas fechas" (ambiguous date)
COCUY_TURN_5 = {
    "interest_level": "High",
    "budget_status": "NotMentioned",
    "purchase_urgency": "ShortTerm",
    "has_decision_authority": False,
    "explicit_human_request": False,
    "plan_and_date_confirmed": False,
}

# Cocuy turn 6: "el 14 de marzo" with plan from history
COCUY_TURN_6 = {
    "interest_level": "High",
    "budget_status": "NotMentioned",
    "purchase_urgency": "ShortTerm",
    "has_decision_authority": False,
    "explicit_human_request": False,
    "plan_and_date_confirmed": True,
}


def _score(**kwargs: object) -> dict:
    return calculate_lead_score(**kwargs)  # type: ignore[arg-type]


def test_cocuy_turn_4_booking_intent_does_not_qualify() -> None:
    result = _score(**COCUY_TURN_4)
    assert result["qualifies"] is False
    assert result["score"] == 30


def test_cocuy_turn_5_ambiguous_dates_do_not_qualify() -> None:
    result = _score(**COCUY_TURN_5)
    assert result["qualifies"] is False
    assert result["score"] < 70


def test_cocuy_turn_6_plan_and_date_confirmed_fast_tracks() -> None:
    result = _score(**COCUY_TURN_6)
    assert result["qualifies"] is True
    assert result["score"] == 100
    assert result["breakdown"]["fast_track"]["reason"] == "plan_and_date_confirmed"


def test_explicit_human_request_fast_tracks() -> None:
    result = _score(
        interest_level="Low",
        budget_status="NotMentioned",
        purchase_urgency="Uncertain",
        has_decision_authority=False,
        explicit_human_request=True,
        plan_and_date_confirmed=False,
    )
    assert result["qualifies"] is True
    assert result["score"] == 100
    assert result["breakdown"]["fast_track"]["reason"] == "explicit_human_request"


def test_insufficient_budget_disqualifies() -> None:
    result = _score(
        interest_level="High",
        budget_status="Insufficient",
        purchase_urgency="Immediate",
        has_decision_authority=True,
        explicit_human_request=False,
        plan_and_date_confirmed=True,
    )
    assert result["qualifies"] is False
    assert result["score"] == 0
    assert result["breakdown"]["disqualified"]["reason"] == "insufficient_budget"


# Flandes session final turn: High + ShortTerm + authority, budget not mentioned
FLANDES_HANDOFF = {
    "interest_level": "High",
    "budget_status": "NotMentioned",
    "purchase_urgency": "ShortTerm",
    "has_decision_authority": True,
    "explicit_human_request": False,
    "plan_and_date_confirmed": False,
}


def test_high_intent_without_date_or_budget_does_not_qualify() -> None:
    result = _score(**FLANDES_HANDOFF)
    assert result["qualifies"] is False
    assert result["score"] == 65
    assert "fast_track" not in result["breakdown"]


def test_high_intent_without_authority_does_not_qualify() -> None:
    result = _score(
        interest_level="High",
        budget_status="NotMentioned",
        purchase_urgency="ShortTerm",
        has_decision_authority=False,
        explicit_human_request=False,
        plan_and_date_confirmed=False,
    )
    assert result["qualifies"] is False
    assert result["score"] == 45


# Booking with relative date window: plan known + explicit reserve + near-term window
BOOKING_RELATIVE_DATE = {
    "interest_level": "High",
    "budget_status": "NotMentioned",
    "purchase_urgency": "ShortTerm",
    "has_decision_authority": False,
    "explicit_human_request": False,
    "plan_and_date_confirmed": True,
}

# Solo traveler with booking intent: High + ShortTerm + decision authority
SOLO_TRAVELER_AUTHORITY = {
    "interest_level": "High",
    "budget_status": "NotMentioned",
    "purchase_urgency": "ShortTerm",
    "has_decision_authority": True,
    "explicit_human_request": False,
    "plan_and_date_confirmed": False,
}


def test_booking_relative_date_fast_tracks() -> None:
    result = _score(**BOOKING_RELATIVE_DATE)
    assert result["qualifies"] is True
    assert result["score"] == 100
    assert result["breakdown"]["fast_track"]["reason"] == "plan_and_date_confirmed"


def test_solo_traveler_authority_without_date_does_not_qualify() -> None:
    result = _score(**SOLO_TRAVELER_AUTHORITY)
    assert result["qualifies"] is False
    assert result["score"] == 65
    assert "fast_track" not in result["breakdown"]


def test_medium_interest_does_not_fast_track() -> None:
    result = _score(
        interest_level="Medium",
        budget_status="NotMentioned",
        purchase_urgency="ShortTerm",
        has_decision_authority=True,
        explicit_human_request=False,
        plan_and_date_confirmed=False,
    )
    assert result["qualifies"] is False
    assert result["score"] < 70
