"""Integration tests: polluted session history must not reach customer LLM."""

from __future__ import annotations

import json

import pytest
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from app.subagents.bridge.agent import bridge_agent
from app.subagents.customer.agent import customer_agent
from chatty_agent_common.eval_guards import find_forbidden_leaks
from chatty_agent_common.llm_contents import filter_internal_bant_contents


def _bant_json(**overrides: object) -> str:
    payload = {
        "interest_level": "Medium",
        "budget_status": "NotMentioned",
        "purchase_urgency": "Uncertain",
        "has_decision_authority": False,
        "explicit_human_request": False,
        "plan_and_date_confirmed": False,
    }
    payload.update(overrides)
    return json.dumps(payload)


def _text_content(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part(text=text)])


def _polluted_whale_history() -> list[types.Content]:
    """Simulates turn-2 session after qualifier leaked JSON into events."""
    return [
        _text_content("user", "Hola"),
        _text_content(
            "model",
            "¡Hola! Soy Amaru tu guía digital del equipo Xperiencia 🏔️\n"
            "¿Qué tipo de aventura o destino tienes en mente hoy?",
        ),
        _text_content("model", _bant_json()),
        _text_content("user", "Avistamiento de ballenas"),
    ]


def test_filter_removes_qualifier_bant_from_polluted_whale_history() -> None:
    from chatty_agent_common.qualification import parse_bant_signals

    filtered = filter_internal_bant_contents(_polluted_whale_history())

    assert len(filtered) == 3
    assert filtered[-1].parts[0].text == "Avistamiento de ballenas"
    assert all(
        parse_bant_signals(part.text) is None
        for content in filtered
        for part in content.parts
        if part.text
    )


@pytest.mark.asyncio
async def test_customer_before_model_callback_strips_bant_json() -> None:
    request = LlmRequest(contents=_polluted_whale_history())
    callback = customer_agent.before_model_callback
    assert callback is not None

    result = await callback(None, request)  # type: ignore[arg-type]

    assert result is None
    assert len(request.contents) == 3
    assert request.contents[-1].parts[0].text == "Avistamiento de ballenas"


@pytest.mark.asyncio
async def test_bridge_before_model_callback_strips_bant_json() -> None:
    request = LlmRequest(contents=_polluted_whale_history())
    callback = bridge_agent.before_model_callback
    assert callback is not None

    result = await callback(None, request)  # type: ignore[arg-type]

    assert result is None
    assert len(request.contents) == 3


def test_forbidden_guard_catches_leaked_meta_commentary() -> None:
    leaked = (
        "Dado que el último mensaje del usuario fue puramente informativo "
        "(ejemplo de handoff y estado interno), esperaré su próxima "
        "intervención conversacional."
    )
    assert find_forbidden_leaks(leaked)
