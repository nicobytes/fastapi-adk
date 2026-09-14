"""Deterministic eval metric: fail when internal jargon leaks to the user."""

from chatty_agent_common.eval_guards import find_forbidden_leaks


def evaluate(instance):
    text = str(instance.get("response") or "")
    leaks = find_forbidden_leaks(text)
    if leaks:
        return {
            "score": 0,
            "explanation": f"Forbidden user-facing leak(s): {', '.join(leaks)}",
        }
    return {"score": 1, "explanation": "No forbidden internal leaks detected."}
