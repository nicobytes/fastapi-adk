"""Vertex Sessions reject events with an empty invocation_id."""

from __future__ import annotations

from google.adk.events import Event
from google.genai import types

from chatty_agent_common.adk_events import ensure_invocation_id, model_text_event


class _Ctx:
    def __init__(
        self, invocation_id: str = "inv-1", branch: str | None = "root"
    ) -> None:
        self.invocation_id = invocation_id
        self.branch = branch


def test_model_text_event_sets_invocation_id() -> None:
    event = model_text_event(_Ctx(), "hola", author="amaru")

    assert event.invocation_id == "inv-1"
    assert event.branch == "root"
    assert event.author == "amaru"
    assert event.content is not None
    assert event.content.parts[0].text == "hola"
    assert event.actions.state_delta == {}


def test_model_text_event_attaches_state_delta() -> None:
    from chatty_agent_common.adk_events import CLEAR_ACTIVATE_STATE

    event = model_text_event(
        _Ctx(),
        "nudge",
        author="amaru",
        state=CLEAR_ACTIVATE_STATE,
    )

    assert event.actions.state_delta == CLEAR_ACTIVATE_STATE


def test_state_delta_event_has_no_content() -> None:
    from chatty_agent_common.adk_events import (
        CLEAR_ACTIVATE_STATE,
        state_delta_event,
    )

    event = state_delta_event(_Ctx(), author="amaru", state=CLEAR_ACTIVATE_STATE)

    assert event.invocation_id == "inv-1"
    assert event.content is None
    assert event.actions.state_delta == CLEAR_ACTIVATE_STATE


def test_ensure_invocation_id_fills_blank() -> None:
    blank = Event(
        author="customer",
        content=types.Content(role="model", parts=[types.Part(text="ok")]),
    )
    assert blank.invocation_id == ""

    filled = ensure_invocation_id(blank, _Ctx("inv-2", None))

    assert filled.invocation_id == "inv-2"
    assert filled.content is not None
    assert filled.content.parts[0].text == "ok"


def test_ensure_invocation_id_keeps_existing() -> None:
    original = Event(
        invocation_id="already-set",
        author="customer",
        content=types.Content(role="model", parts=[types.Part(text="ok")]),
    )

    out = ensure_invocation_id(original, _Ctx("other"))

    assert out.invocation_id == "already-set"
    assert out is original
