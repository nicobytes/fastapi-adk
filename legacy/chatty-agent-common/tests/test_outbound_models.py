"""Pydantic validation for outbound intent models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chatty_agent_common.outbound.models import (
    ButtonsIntent,
    IntentBatchResult,
    IntentToolResult,
    ListIntent,
    LocationIntent,
    ReplyButton,
    TextIntent,
)


def test_text_intent_requires_body() -> None:
    with pytest.raises(ValidationError):
        TextIntent(body="")


def test_buttons_max_three_and_title_length() -> None:
    buttons = [ReplyButton(id=f"b{i}", title=f"Opt {i}") for i in range(3)]
    intent = ButtonsIntent(body="Pick one", buttons=buttons)
    assert intent.type == "buttons"
    assert len(intent.buttons) == 3

    with pytest.raises(ValidationError):
        ButtonsIntent(
            body="x",
            buttons=[ReplyButton(id="a", title="This title is way too long")],
        )

    with pytest.raises(ValidationError):
        ButtonsIntent(
            body="x",
            buttons=[ReplyButton(id=f"b{i}", title=str(i)) for i in range(4)],
        )


def test_list_intent_limits() -> None:
    intent = ListIntent(
        body="Choose",
        button_label="Options",
        sections=[
            {
                "title": "Sec",
                "rows": [{"id": "r1", "title": "Row 1"}],
            }
        ],
    )
    assert intent.button_label == "Options"


def test_location_bounds() -> None:
    LocationIntent(latitude=-17.8, longitude=-63.18, name="HQ")
    with pytest.raises(ValidationError):
        LocationIntent(latitude=100, longitude=0)


def test_intent_tool_result_stable_envelope() -> None:
    result = IntentToolResult(intent=TextIntent(body="hola"))
    dumped = result.to_response_dict()
    assert dumped["kind"] == "outbound_intent"
    assert dumped["intent"]["type"] == "text"
    assert dumped["intent"]["body"] == "hola"


def test_intent_batch_result_serializes_text_then_location() -> None:
    dumped = IntentBatchResult(
        intents=[
            TextIntent(body="Cita confirmada"),
            LocationIntent(
                latitude=-19.040035,
                longitude=-65.244153,
                name="Be Unique — Sucre",
            ),
        ]
    ).to_response_dict()
    assert dumped["kind"] == "outbound_intent_batch"
    assert [item["type"] for item in dumped["intents"]] == ["text", "location"]
    assert dumped["intents"][0]["body"] == "Cita confirmada"
    assert dumped["intents"][1]["name"] == "Be Unique — Sucre"


def test_intent_batch_result_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        IntentBatchResult(intents=[])
