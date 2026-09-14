"""Canonical sede catalog and send_sede_location envelopes."""

from __future__ import annotations

from types import SimpleNamespace

from app.subagents.customer.tools.sede_location import (
    SEDE_COCHABAMBA,
    SEDE_SUCRE,
    resolve_sede_pin,
    send_sede_location,
)


def _ctx(state: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(state=state or {})


def test_resolve_sede_pin_aliases() -> None:
    assert resolve_sede_pin("Sucre") == [SEDE_SUCRE]
    assert resolve_sede_pin("sede_sucre") == [SEDE_SUCRE]
    assert resolve_sede_pin("Cochabamba") == [SEDE_COCHABAMBA]
    assert resolve_sede_pin("sede_cochabamba") == [SEDE_COCHABAMBA]
    assert resolve_sede_pin("ambas") == [SEDE_SUCRE, SEDE_COCHABAMBA]
    assert resolve_sede_pin("ambas sedes") == [SEDE_SUCRE, SEDE_COCHABAMBA]
    assert resolve_sede_pin("Santa Cruz") == []
    assert resolve_sede_pin("") == []


def test_send_location_only_one_sede() -> None:
    out = send_sede_location("Sucre", _ctx())  # type: ignore[arg-type]
    assert out["kind"] == "outbound_intent"
    intent = out["intent"]
    assert intent["type"] == "location"
    assert intent["latitude"] == SEDE_SUCRE.latitude
    assert intent["longitude"] == SEDE_SUCRE.longitude
    assert intent["name"] == SEDE_SUCRE.display_name
    assert intent["address"] == SEDE_SUCRE.address
    assert "latitude" not in send_sede_location.__annotations__


def test_send_ambas_is_batch_sucre_then_cochabamba() -> None:
    out = send_sede_location("ambas", _ctx())  # type: ignore[arg-type]
    assert out["kind"] == "outbound_intent_batch"
    intents = out["intents"]
    assert [i["type"] for i in intents] == ["location", "location"]
    assert intents[0]["name"] == SEDE_SUCRE.display_name
    assert intents[0]["latitude"] == SEDE_SUCRE.latitude
    assert intents[1]["name"] == SEDE_COCHABAMBA.display_name
    assert intents[1]["latitude"] == SEDE_COCHABAMBA.latitude


def test_unknown_sede_returns_error_without_pin() -> None:
    out = send_sede_location("La Paz", _ctx())  # type: ignore[arg-type]
    assert out["status"] == "error"
    assert "kind" not in out
    assert "intent" not in out


def test_empty_sede_falls_back_to_active_sede() -> None:
    out = send_sede_location("", _ctx({"active_sede": "Cochabamba"}))  # type: ignore[arg-type]
    assert out["kind"] == "outbound_intent"
    assert out["intent"]["name"] == SEDE_COCHABAMBA.display_name


def test_empty_sede_without_active_is_error() -> None:
    out = send_sede_location("", _ctx())  # type: ignore[arg-type]
    assert out["status"] == "error"


def test_body_plus_one_sede_is_text_then_location() -> None:
    body = (
        "Cita confirmada en Sucre, Ana, depilación axilas, "
        "miércoles 2 de septiembre a las 10:00 AM."
    )
    out = send_sede_location("Sucre", _ctx(), body=body)  # type: ignore[arg-type]
    assert out["kind"] == "outbound_intent_batch"
    intents = out["intents"]
    assert [i["type"] for i in intents] == ["text", "location"]
    assert intents[0]["body"] == body
    assert intents[1]["name"] == SEDE_SUCRE.display_name
    assert intents[1]["latitude"] == SEDE_SUCRE.latitude
    assert intents[1]["longitude"] == SEDE_SUCRE.longitude


def test_blank_body_is_location_only() -> None:
    out = send_sede_location("Sucre", _ctx(), body="   ")  # type: ignore[arg-type]
    assert out["kind"] == "outbound_intent"
    assert out["intent"]["type"] == "location"


def test_body_plus_ambas_is_error() -> None:
    out = send_sede_location("ambas", _ctx(), body="Cita confirmada")  # type: ignore[arg-type]
    assert out["status"] == "error"
    assert "kind" not in out
