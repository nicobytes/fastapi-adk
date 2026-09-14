"""Tests for internal BANT content filtering before LLM calls."""

from __future__ import annotations

import json

import pytest
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from chatty_agent_common.llm_contents import (
    filter_internal_bant_contents,
    strip_internal_bant_contents,
)

_BANT_JSON = {
    "interest_level": "Medium",
    "budget_status": "NotMentioned",
    "purchase_urgency": "Uncertain",
    "has_decision_authority": False,
    "explicit_human_request": False,
    "plan_and_date_confirmed": False,
}


def _text_content(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part(text=text)])


def test_filter_internal_bant_contents_removes_bant_json() -> None:
    contents = [
        _text_content("user", "Hola"),
        _text_content("model", "¡Hola! Soy Amaru."),
        _text_content("user", "Avistamiento de ballenas"),
        _text_content("model", json.dumps(_BANT_JSON)),
    ]

    filtered = filter_internal_bant_contents(contents)

    assert len(filtered) == 3
    assert filtered[-1].parts[0].text == "Avistamiento de ballenas"


def test_filter_internal_bant_contents_keeps_normal_messages() -> None:
    contents = [
        _text_content("user", "Hola"),
        _text_content("model", "¡Hola! Soy Amaru."),
        _text_content("user", "Avistamiento de ballenas"),
    ]

    filtered = filter_internal_bant_contents(contents)

    assert filtered == contents


def test_filter_internal_bant_contents_keeps_partial_json() -> None:
    partial = json.dumps({"interest_level": "High"})
    contents = [
        _text_content("user", "Hola"),
        _text_content("model", partial),
    ]

    filtered = filter_internal_bant_contents(contents)

    assert filtered == contents


@pytest.mark.asyncio
async def test_strip_internal_bant_contents_mutates_request() -> None:
    request = LlmRequest(
        contents=[
            _text_content("user", "Avistamiento de ballenas"),
            _text_content("model", json.dumps(_BANT_JSON)),
        ]
    )

    result = await strip_internal_bant_contents(None, request)  # type: ignore[arg-type]

    assert result is None
    assert len(request.contents) == 1
    assert request.contents[0].parts[0].text == "Avistamiento de ballenas"


def test_filter_drops_chatty_activate_token() -> None:
    contents = [
        _text_content("user", "Hola"),
        _text_content("model", "¡Hola! Soy Amaru."),
        _text_content("user", "[CHATTY_ACTIVATE]"),
        _text_content("model", "¿Todo bien por ahí?"),
        _text_content("user", "si quero ir a montaña"),
    ]

    filtered = filter_internal_bant_contents(contents)

    assert [c.parts[0].text for c in filtered] == [
        "Hola",
        "¡Hola! Soy Amaru.",
        "¿Todo bien por ahí?",
        "si quero ir a montaña",
    ]


def test_filter_drops_chatty_activate_fallback_payload() -> None:
    contents = [
        _text_content(
            "user",
            "[CHATTY_ACTIVATE]\nstage=first_contact\nnote=El usuario no respondió.",
        ),
        _text_content("user", "quiero montaña"),
    ]

    filtered = filter_internal_bant_contents(contents)

    assert len(filtered) == 1
    assert filtered[0].parts[0].text == "quiero montaña"
