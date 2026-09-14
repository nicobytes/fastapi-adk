"""Playground outbound mirror callbacks (ADK_DEV_MODE only)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from google.genai import types

from chatty_agent_common.outbound.playground import (
    PLAYGROUND_OUTBOUND_PREVIEW_KEY,
    capture_outbound_for_playground,
    clear_outbound_preview_if_model_text,
    is_adk_dev_mode,
    mirror_outbound_for_playground,
    summarize_outbound_intent,
)
from chatty_agent_common.outbound.tools import (
    reply_with_buttons,
    reply_with_list,
    reply_with_location,
    reply_with_text,
    send_template,
)


def test_is_adk_dev_mode(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    assert is_adk_dev_mode() is True
    monkeypatch.setenv("ADK_DEV_MODE", "false")
    assert is_adk_dev_mode() is False
    monkeypatch.delenv("ADK_DEV_MODE", raising=False)
    assert is_adk_dev_mode() is False


def test_summarize_outbound_intent_types() -> None:
    assert summarize_outbound_intent({"type": "text", "body": "Hola"}) == "Hola"
    assert (
        summarize_outbound_intent(
            {
                "type": "buttons",
                "body": "Elige",
                "buttons": [
                    {"id": "sede_sucre", "title": "Sucre"},
                    {"id": "sede_cochabamba", "title": "Cochabamba"},
                ],
            }
        )
        == "Elige\n\n[Sucre · sede_sucre] [Cochabamba · sede_cochabamba]"
    )
    assert summarize_outbound_intent({"type": "buttons", "body": "Elige"}) == "Elige"
    assert (
        summarize_outbound_intent(
            {
                "type": "list",
                "body": "Menú",
                "buttonLabel": "Ver opciones",
                "sections": [
                    {
                        "title": "Tratamientos",
                        "rows": [
                            {"id": "laser_id", "title": "Láser"},
                            {"id": "botox_id", "title": "Botox"},
                        ],
                    }
                ],
            }
        )
        == "Menú\n\n[Ver opciones]\nTratamientos:\n• Láser (laser_id)\n• Botox (botox_id)"
    )
    assert summarize_outbound_intent({"type": "list", "body": "Menú"}) == "Menú"
    assert (
        summarize_outbound_intent(
            {"type": "location", "latitude": 1.0, "longitude": 2.0, "name": "Sede"}
        )
        == "Sede"
    )
    assert (
        summarize_outbound_intent(
            {"type": "location", "latitude": 1.0, "longitude": 2.0}
        )
        == "📍 1.0, 2.0"
    )
    assert (
        summarize_outbound_intent({"type": "template", "name": "hello_world"})
        == "[template:hello_world]"
    )


def test_capture_buttons_and_list_preview(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state: dict = {}
    tool_context = SimpleNamespace(state=state)
    capture_outbound_for_playground(
        MagicMock(),
        {},
        tool_context,  # type: ignore[arg-type]
        reply_with_buttons(
            "Elige sede",
            [
                {"id": "sede_sucre", "title": "Sucre"},
                {"id": "sede_cochabamba", "title": "Cochabamba"},
            ],
        ),
    )
    assert (
        state[PLAYGROUND_OUTBOUND_PREVIEW_KEY]
        == "Elige sede\n\n[Sucre · sede_sucre] [Cochabamba · sede_cochabamba]"
    )

    state.clear()
    capture_outbound_for_playground(
        MagicMock(),
        {},
        tool_context,  # type: ignore[arg-type]
        reply_with_list(
            "Elige servicio",
            "Ver opciones",
            [
                {
                    "title": "Tratamientos",
                    "rows": [
                        {"id": "laser_id", "title": "Láser"},
                        {"id": "botox_id", "title": "Botox"},
                    ],
                }
            ],
        ),
    )
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == (
        "Elige servicio\n\n[Ver opciones]\n"
        "Tratamientos:\n• Láser (laser_id)\n• Botox (botox_id)"
    )


def test_capture_noop_without_dev_mode(monkeypatch) -> None:
    monkeypatch.delenv("ADK_DEV_MODE", raising=False)
    state: dict = {}
    tool_context = SimpleNamespace(state=state)
    out = capture_outbound_for_playground(
        MagicMock(name="reply_with_text"),
        {},
        tool_context,  # type: ignore[arg-type]
        reply_with_text("Hola"),
    )
    assert out is None
    assert PLAYGROUND_OUTBOUND_PREVIEW_KEY not in state


def test_capture_stores_preview_in_dev_mode(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state: dict = {}
    tool_context = SimpleNamespace(state=state)
    out = capture_outbound_for_playground(
        MagicMock(name="reply_with_text"),
        {},
        tool_context,  # type: ignore[arg-type]
        reply_with_text("Hola playground"),
    )
    assert out is None
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == "Hola playground"


def test_capture_accumulates_multiple_intents(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state: dict = {}
    tool_context = SimpleNamespace(state=state)
    capture_outbound_for_playground(
        MagicMock(),
        {},
        tool_context,  # type: ignore[arg-type]
        reply_with_text("Uno"),
    )
    capture_outbound_for_playground(
        MagicMock(),
        {},
        tool_context,  # type: ignore[arg-type]
        reply_with_location(-17.78, -63.18, name="Oficina"),
    )
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == "Uno\n\nOficina"


def test_capture_batch_concatenates_previews(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state: dict = {}
    tool_context = SimpleNamespace(state=state)
    capture_outbound_for_playground(
        MagicMock(),
        {},
        tool_context,  # type: ignore[arg-type]
        {
            "kind": "outbound_intent_batch",
            "intents": [
                {"type": "text", "body": "Cita confirmada"},
                {
                    "type": "location",
                    "latitude": -19.040035,
                    "longitude": -65.244153,
                    "name": "Be Unique — Sucre",
                },
            ],
        },
    )
    assert (
        state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == "Cita confirmada\n\nBe Unique — Sucre"
    )


def test_capture_ignores_non_outbound(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state: dict = {}
    tool_context = SimpleNamespace(state=state)
    capture_outbound_for_playground(
        MagicMock(),
        {},
        tool_context,  # type: ignore[arg-type]
        {"status": "ok"},
    )
    assert PLAYGROUND_OUTBOUND_PREVIEW_KEY not in state


def test_mirror_returns_content_and_clears_state(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state = {PLAYGROUND_OUTBOUND_PREVIEW_KEY: "Texto visible"}
    callback_context = SimpleNamespace(state=state)
    content = mirror_outbound_for_playground(callback_context)  # type: ignore[arg-type]
    assert content is not None
    assert content.role == "model"
    assert content.parts is not None
    assert content.parts[0].text == "Texto visible"
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == ""


def test_mirror_noop_without_preview(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    callback_context = SimpleNamespace(state={})
    assert mirror_outbound_for_playground(callback_context) is None  # type: ignore[arg-type]


def test_mirror_noop_without_dev_mode(monkeypatch) -> None:
    monkeypatch.delenv("ADK_DEV_MODE", raising=False)
    state = {PLAYGROUND_OUTBOUND_PREVIEW_KEY: "hidden"}
    callback_context = SimpleNamespace(state=state)
    assert mirror_outbound_for_playground(callback_context) is None  # type: ignore[arg-type]
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == "hidden"


def test_capture_template_preview(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state: dict = {}
    tool_context = SimpleNamespace(state=state)
    capture_outbound_for_playground(
        MagicMock(),
        {},
        tool_context,  # type: ignore[arg-type]
        send_template("hello_world", "es"),
    )
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == "[template:hello_world]"


def test_clear_preview_when_model_writes_text(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state = {PLAYGROUND_OUTBOUND_PREVIEW_KEY: "from tool"}
    callback_context = SimpleNamespace(state=state)
    llm_response = SimpleNamespace(
        content=types.Content(
            role="model",
            parts=[types.Part(text="from model")],
        )
    )
    assert (
        clear_outbound_preview_if_model_text(
            callback_context,  # type: ignore[arg-type]
            llm_response,  # type: ignore[arg-type]
        )
        is None
    )
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == ""


def test_clear_preview_keeps_state_for_tool_only_model_turn(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state = {PLAYGROUND_OUTBOUND_PREVIEW_KEY: "from tool"}
    callback_context = SimpleNamespace(state=state)
    llm_response = SimpleNamespace(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="reply_with_text",
                        args={"body": "x"},
                    )
                )
            ],
        )
    )
    clear_outbound_preview_if_model_text(
        callback_context,  # type: ignore[arg-type]
        llm_response,  # type: ignore[arg-type]
    )
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == "from tool"


def test_mirror_skips_when_session_already_has_model_text(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state = {PLAYGROUND_OUTBOUND_PREVIEW_KEY: "duplicated"}
    session = SimpleNamespace(
        events=[
            SimpleNamespace(
                content=types.Content(
                    role="user",
                    parts=[types.Part(text="hola")],
                )
            ),
            SimpleNamespace(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="already shown")],
                )
            ),
        ]
    )
    callback_context = SimpleNamespace(state=state, session=session)
    assert mirror_outbound_for_playground(callback_context) is None  # type: ignore[arg-type]
    assert state[PLAYGROUND_OUTBOUND_PREVIEW_KEY] == ""
