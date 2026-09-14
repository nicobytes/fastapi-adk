from __future__ import annotations

from typing import Any, Literal

InterestLevel = Literal["Low", "Medium", "High"]
BudgetStatus = Literal["NotMentioned", "Insufficient", "Aligned"]
PurchaseUrgency = Literal["Immediate", "ShortTerm", "LongTerm", "Uncertain"]

HANDOFF_THRESHOLD = 70


def calculate_lead_score(
    interest_level: InterestLevel,
    budget_status: BudgetStatus,
    purchase_urgency: PurchaseUrgency,
    has_decision_authority: bool,
    explicit_human_request: bool,
    plan_and_date_confirmed: bool = False,
    *,
    threshold: int = HANDOFF_THRESHOLD,
) -> dict[str, Any]:
    """Compute a deterministic BANT qualification score (0-100).

    Uses only criteria extracted from chat history. Does not query databases or
    mutate conversations.

    Args:
        interest_level: Detected interest level (`Low`, `Medium`, `High`).
        budget_status: Budget state (`NotMentioned`, `Insufficient`, `Aligned`).
        purchase_urgency: Purchase urgency (`Immediate`, `ShortTerm`, etc.).
        has_decision_authority: True if the customer can make the purchase decision.
        explicit_human_request: True if they explicitly asked for a human.
        plan_and_date_confirmed: True if they confirmed a plan and concrete date.

    Returns:
        dict with score, threshold, qualifies, and per-criterion breakdown.
    """
    breakdown: dict[str, Any] = {}

    if explicit_human_request:
        breakdown["fast_track"] = {
            "reason": "explicit_human_request",
            "points": 100,
        }
        return {
            "score": 100,
            "threshold": threshold,
            "qualifies": True,
            "breakdown": breakdown,
        }

    if budget_status == "Insufficient":
        breakdown["disqualified"] = {
            "reason": "insufficient_budget",
            "points": 0,
        }
        return {
            "score": 0,
            "threshold": threshold,
            "qualifies": False,
            "breakdown": breakdown,
        }

    if plan_and_date_confirmed:
        breakdown["fast_track"] = {
            "reason": "plan_and_date_confirmed",
            "points": 100,
        }
        return {
            "score": 100,
            "threshold": threshold,
            "qualifies": True,
            "breakdown": breakdown,
        }

    score = 0

    interest_points = {"High": 30, "Medium": 15, "Low": 0}[interest_level]
    breakdown["interest_level"] = {"value": interest_level, "points": interest_points}
    score += interest_points

    urgency_points = {
        "Immediate": 25,
        "ShortTerm": 15,
        "LongTerm": 0,
        "Uncertain": 0,
    }[purchase_urgency]
    breakdown["purchase_urgency"] = {
        "value": purchase_urgency,
        "points": urgency_points,
    }
    score += urgency_points

    budget_points = {
        "Aligned": 25,
        "NotMentioned": 0,
        "Insufficient": 0,
    }[budget_status]
    breakdown["budget_status"] = {"value": budget_status, "points": budget_points}
    score += budget_points

    authority_points = 20 if has_decision_authority else 0
    breakdown["has_decision_authority"] = {
        "value": has_decision_authority,
        "points": authority_points,
    }
    score += authority_points

    return {
        "score": score,
        "threshold": threshold,
        "qualifies": score >= threshold,
        "breakdown": breakdown,
    }
