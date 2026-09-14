"""Instruction bundle: static personality/rules + dynamic session."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.subagents.customer.instructions import STATIC_INSTRUCTION, build_instruction

_PERSONALITY = Path(__file__).resolve().parents[1] / (
    "app/subagents/customer/instructions/personality.md"
)

_TZ_LA_PAZ = ZoneInfo("America/La_Paz")


class _FakeReadonlyContext:
    def __init__(
        self,
        state: dict[str, Any],
        session_id: str | None = "conv-test",
    ) -> None:
        self.state = state
        self.session = type("S", (), {"id": session_id})() if session_id else None


def test_static_instruction_includes_sofia_and_agenda() -> None:
    assert "Sofía" in STATIC_INSTRUCTION
    assert "list_available_days" in STATIC_INSTRUCTION
    assert "list_available_hours" in STATIC_INSTRUCTION
    assert "book_appointment" in STATIC_INSTRUCTION
    assert "check_availability" not in STATIC_INSTRUCTION
    assert "ejemplo de respuesta tras handoff" not in STATIC_INSTRUCTION.lower()
    assert "request_human_handoff" not in STATIC_INSTRUCTION
    assert "{{" not in STATIC_INSTRUCTION
    assert "atención a cliente nuevo" in STATIC_INSTRUCTION.lower() or (
        "Camino principal" in STATIC_INSTRUCTION
    )
    assert "historial interno" in STATIC_INSTRUCTION.lower()


def test_static_instruction_includes_policy_anchors() -> None:
    assert "09:00" in STATIC_INSTRUCTION
    assert "100 Bs" in STATIC_INSTRUCTION
    assert (
        "Cochabamba" in STATIC_INSTRUCTION and "sin costo" in STATIC_INSTRUCTION.lower()
    )
    assert "tarjetas" in STATIC_INSTRUCTION.lower()
    assert (
        "reglas de oro" in STATIC_INSTRUCTION.lower()
        or "Promociones" in STATIC_INSTRUCTION
    )
    assert (
        "Fuente de hechos" in STATIC_INSTRUCTION
        or "Horario, WhatsApp" in STATIC_INSTRUCTION
        or "Horario, dirección" in STATIC_INSTRUCTION
    )


def test_build_instruction_session_state_without_bridge_example() -> None:
    ctx = _FakeReadonlyContext(
        {
            "qualification_score": "40",
            "lead_qualifies": "false",
            "active_sede": "Sucre",
            "customer_name": "Ana",
        }
    )
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "active_sede: Sucre" in text
    assert "customer_name: Ana" in text
    assert "Ejemplo de respuesta tras handoff" not in text
    assert "list_available_days" not in text
    today = datetime.now(_TZ_LA_PAZ).date().isoformat()
    assert f"current_date: {today}" in text
    assert re.search(r"current_weekday: \S+", text)


def test_static_instruction_named_date_protocol() -> None:
    assert "availability_kind" in STATIC_INSTRUCTION
    assert "error_code" in STATIC_INSTRUCTION
    assert "lista corta de descubrimiento" in STATIC_INSTRUCTION
    assert "empty_day" in STATIC_INSTRUCTION
    assert "beyond_horizon" in STATIC_INSTRUCTION
    assert "tan adelante" in STATIC_INSTRUCTION.lower()
    assert (
        "no es día hábil" in STATIC_INSTRUCTION.lower()
        or "no es hábil" in STATIC_INSTRUCTION.lower()
    )


def test_static_instruction_no_date_still_days_first() -> None:
    assert "list_available_days" in STATIC_INSTRUCTION
    lower = STATIC_INSTRUCTION.lower()
    assert "sin" in lower and "from_date" in STATIC_INSTRUCTION
    assert "no nombró" in lower or "no nombró fecha" in lower


def test_static_instruction_reagendar_named_date() -> None:
    assert "Reagendar" in STATIC_INSTRUCTION or "reagendar" in STATIC_INSTRUCTION
    assert (
        "lista anterior" in STATIC_INSTRUCTION.lower()
        or "lista corta" in STATIC_INSTRUCTION.lower()
    )


def test_static_instruction_two_dates_and_window() -> None:
    assert "from_date" in STATIC_INSTRUCTION
    assert "to_date" in STATIC_INSTRUCTION
    assert (
        "próxima semana" in STATIC_INSTRUCTION.lower()
        or "rango" in STATIC_INSTRUCTION.lower()
    )


def test_static_instruction_sede_location_ask() -> None:
    assert "send_sede_location" in STATIC_INSTRUCTION
    assert "pin basta" in STATIC_INSTRUCTION.lower()
    lower = STATIC_INSTRUCTION.lower()
    assert "maps.app.goo.gl" not in STATIC_INSTRUCTION or "sustituto" in lower
    assert (
        "no está en sus tools" in lower or "reply_with_location" in STATIC_INSTRUCTION
    )
    assert "saludo" in lower and "pin" in lower
    assert "solo horario" in lower or "sin pedir mapa" in lower


def test_personality_keeps_maps_links_without_coordinates() -> None:
    text = _PERSONALITY.read_text(encoding="utf-8")
    assert "maps.app.goo.gl" in text
    assert "Calle Destacamento 317" in text
    assert "-19.0401406" not in text
    assert "-65.2444091" not in text
    assert "-17.373292" not in text
    assert "-66.155718" not in text
    assert "latitude" not in text.lower()
    assert "longitude" not in text.lower()


def test_static_instruction_does_not_require_raw_location_tool() -> None:
    assert "reply_with_location" in STATIC_INSTRUCTION
    assert "no está en sus tools" in STATIC_INSTRUCTION.lower()


def test_static_instruction_book_confirmation_sends_pin() -> None:
    assert "body=" in STATIC_INSTRUCTION or "body=…" in STATIC_INSTRUCTION
    assert "send_sede_location(sede, body" in STATIC_INSTRUCTION
    assert "antes" in STATIC_INSTRUCTION.lower() and "pin" in STATIC_INSTRUCTION.lower()
    assert "no reemplaza" in STATIC_INSTRUCTION.lower()
    assert "reply_with_text` solo" in STATIC_INSTRUCTION or (
        "no use `reply_with_text` solo" in STATIC_INSTRUCTION.lower()
    )


def test_static_instruction_reagendar_sends_pin_cancel_does_not() -> None:
    reagendar_start = STATIC_INSTRUCTION.find("## Reagendar cita existente")
    cancel_start = STATIC_INSTRUCTION.find("## Cancelar cita existente")
    protocolo_start = STATIC_INSTRUCTION.find("## Protocolo de turno")
    assert reagendar_start != -1 and cancel_start != -1 and protocolo_start != -1
    reagendar = STATIC_INSTRUCTION[reagendar_start:cancel_start]
    cancel = STATIC_INSTRUCTION[cancel_start:protocolo_start]
    assert "send_sede_location" in reagendar
    assert "body" in reagendar
    assert "send_sede_location" not in cancel
    assert "reply_with_text" in cancel
    assert "sin pin" in cancel.lower() or "no pin" in cancel.lower()


def test_build_instruction_session_allows_named_date_outside_list() -> None:
    ctx = _FakeReadonlyContext({"active_sede": "Sucre"})
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]
    assert "lista corta" in text.lower() or "available_days" in text
    assert "aunque no esté" in text.lower() or "aunque no este" in text.lower()


def test_static_instruction_promo_golden_rules() -> None:
    lower = STATIC_INSTRUCTION.lower()
    assert "activa" in lower
    assert "publicable" in lower
    assert "vigencia" in lower or "current_date" in STATIC_INSTRUCTION


def test_static_instruction_duration_from_skills() -> None:
    assert "Tiempo total" in STATIC_INSTRUCTION
    assert "30" in STATIC_INSTRUCTION
    assert "search_context" not in STATIC_INSTRUCTION
    assert "load_skill" in STATIC_INSTRUCTION


def test_static_instruction_faciales_anticipo_both_cities() -> None:
    assert "100 Bs" in STATIC_INSTRUCTION
    lower = STATIC_INSTRUCTION.lower()
    assert "faciales" in lower
    assert "cochabamba" in lower
    assert "salvo faciales" in lower or "ambas sedes" in lower


def test_static_instruction_includes_ctwa_sede_first() -> None:
    assert "ctwa_ad_body" in STATIC_INSTRUCTION
    assert "ctwa_plan_hint" in STATIC_INSTRUCTION
    assert "ctwa_handled" in STATIC_INSTRUCTION
    lower = STATIC_INSTRUCTION.lower()
    assert "botones" in lower
    assert "tratamiento ya nombrado" in lower


def test_build_instruction_includes_ctwa_block_when_state_set() -> None:
    ctx = _FakeReadonlyContext(
        {
            "ctwa_ad_body": "Hidrafacial",
            "ctwa_plan_hint": "Bienvenida Hidrafacial",
        }
    )
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "Origen CTWA" in text
    assert "Hidrafacial" in text
    assert "Bienvenida Hidrafacial" in text
    assert "tratamiento ya nombrado" in text


def test_build_instruction_omits_ctwa_block_when_handled() -> None:
    ctx = _FakeReadonlyContext(
        {
            "ctwa_ad_body": "Hidrafacial",
            "ctwa_plan_hint": "Bienvenida Hidrafacial",
            "ctwa_handled": "true",
        }
    )
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "Origen CTWA" not in text
    assert "Hidrafacial" not in text
    assert "Bienvenida Hidrafacial" not in text


def test_build_instruction_omits_ctwa_block_without_ad_body() -> None:
    ctx = _FakeReadonlyContext(
        {
            "ctwa_plan_hint": "ignored without ad body",
        }
    )
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "Origen CTWA" not in text
    assert "ignored without ad body" not in text
