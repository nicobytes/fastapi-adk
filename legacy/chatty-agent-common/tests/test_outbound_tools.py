"""Outbound tools are pure (no network) and registry is opt-in."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from chatty_agent_common.outbound.registry import get_outbound_intent_tools
from chatty_agent_common.outbound.tools import (
    reply_with_buttons,
    reply_with_list,
    reply_with_location,
    reply_with_text,
    send_template,
)
from chatty_agent_common.outbound.turn_control import stop_turn_after_outbound_intent


def test_reply_with_text_envelope() -> None:
    out = reply_with_text("Hola")
    assert out["kind"] == "outbound_intent"
    assert out["intent"] == {"type": "text", "body": "Hola"}


def test_reply_with_buttons() -> None:
    out = reply_with_buttons(
        "Elige",
        buttons=[{"id": "a", "title": "Sí"}, {"id": "b", "title": "No"}],
    )
    assert out["intent"]["type"] == "buttons"
    assert len(out["intent"]["buttons"]) == 2


def test_reply_with_buttons_accepts_json_string_items() -> None:
    """Gemini sometimes stringifies nested button objects in tool args."""
    out = reply_with_buttons(
        "Elige sede",
        buttons=[
            '{"id":"sede_sucre","title":"Sucre"}',
            '{"id":"sede_cochabamba","title":"Cochabamba"}',
        ],
    )
    assert out["intent"]["type"] == "buttons"
    assert [b["id"] for b in out["intent"]["buttons"]] == [
        "sede_sucre",
        "sede_cochabamba",
    ]


def test_reply_with_buttons_accepts_bare_title_strings() -> None:
    """Gemini sometimes passes button titles as plain strings."""
    out = reply_with_buttons("Elige sede", buttons=["Sucre", "Cochabamba"])
    assert out["intent"]["type"] == "buttons"
    assert [b["title"] for b in out["intent"]["buttons"]] == ["Sucre", "Cochabamba"]
    assert [b["id"] for b in out["intent"]["buttons"]] == ["sucre", "cochabamba"]


def test_reply_with_list() -> None:
    out = reply_with_list(
        "Menú",
        "Ver",
        sections=[{"title": "S", "rows": [{"id": "1", "title": "Uno"}]}],
    )
    assert out["intent"]["type"] == "list"
    assert out["intent"]["buttonLabel"] == "Ver"


def test_reply_with_list_truncates_to_first_10_rows() -> None:
    """WhatsApp max is 10 rows; oversize input must not raise TOOL_ERROR."""
    rows = [{"id": f"r{i}", "title": f"{i:02d}:00"} for i in range(16)]
    out = reply_with_list(
        "Horarios",
        "Elegir hora",
        sections=[{"title": "Horarios", "rows": rows}],
    )
    assert out["intent"]["type"] == "list"
    kept = out["intent"]["sections"][0]["rows"]
    assert len(kept) == 10
    assert [r["id"] for r in kept] == [f"r{i}" for i in range(10)]


def test_reply_with_list_truncates_across_sections() -> None:
    out = reply_with_list(
        "Opciones",
        "Ver",
        sections=[
            {
                "title": "A",
                "rows": [{"id": f"a{i}", "title": f"A{i}"} for i in range(7)],
            },
            {
                "title": "B",
                "rows": [{"id": f"b{i}", "title": f"B{i}"} for i in range(7)],
            },
        ],
    )
    sections = out["intent"]["sections"]
    total = sum(len(s["rows"]) for s in sections)
    assert total == 10
    assert len(sections[0]["rows"]) == 7
    assert len(sections[1]["rows"]) == 3


def test_reply_with_location() -> None:
    out = reply_with_location(-17.78, -63.18, name="Oficina")
    assert out["intent"]["type"] == "location"
    assert out["intent"]["latitude"] == -17.78


def test_send_template() -> None:
    out = send_template("hello_world", "es")
    assert out["intent"]["type"] == "template"
    assert out["intent"]["name"] == "hello_world"


def test_registry_default_excludes_template() -> None:
    tools = get_outbound_intent_tools()
    names = {t.__name__ for t in tools}
    assert "reply_with_text" in names
    assert "send_template" not in names


def test_registry_opt_in_template() -> None:
    tools = get_outbound_intent_tools(enabled={"reply_with_text", "send_template"})
    names = {t.__name__ for t in tools}
    assert names == {"reply_with_text", "send_template"}


def test_tools_have_no_meta_env_requirement(monkeypatch) -> None:
    monkeypatch.delenv("WHATSAPP_FB_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    assert reply_with_text("ok")["intent"]["body"] == "ok"


def test_stop_turn_after_outbound_intent_sets_skip_summarization() -> None:
    tool_context = MagicMock()
    tool_context.actions = SimpleNamespace(skip_summarization=False)
    result = stop_turn_after_outbound_intent(
        MagicMock(),
        {},
        tool_context,
        {"kind": "outbound_intent", "intent": {"type": "text", "body": "Hola"}},
    )
    assert result is None
    assert tool_context.actions.skip_summarization is True


def test_stop_turn_after_outbound_intent_batch() -> None:
    tool_context = MagicMock()
    tool_context.actions = SimpleNamespace(skip_summarization=False)
    result = stop_turn_after_outbound_intent(
        MagicMock(),
        {},
        tool_context,
        {
            "kind": "outbound_intent_batch",
            "intents": [
                {"type": "text", "body": "Cita"},
                {"type": "location", "latitude": 1, "longitude": 2},
            ],
        },
    )
    assert result is None
    assert tool_context.actions.skip_summarization is True


def test_stop_turn_ignores_non_outbound_response() -> None:
    tool_context = MagicMock()
    tool_context.actions = SimpleNamespace(skip_summarization=False)
    result = stop_turn_after_outbound_intent(
        MagicMock(),
        {},
        tool_context,
        {"status": "ok", "message": "internal tool"},
    )
    assert result is None
    assert tool_context.actions.skip_summarization is False
