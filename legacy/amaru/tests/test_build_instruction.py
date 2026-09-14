"""Instruction bundle: static personality/rules + dynamic session."""

from __future__ import annotations

import asyncio
from typing import Any

from app.subagents.customer.instructions import STATIC_INSTRUCTION, build_instruction


class _FakeReadonlyContext:
    def __init__(
        self,
        state: dict[str, Any],
        session_id: str | None = "conv-test",
    ) -> None:
        self.state = state
        self.session = type("S", (), {"id": session_id})() if session_id else None


def test_static_instruction_includes_amaru() -> None:
    assert "Amaru" in STATIC_INSTRUCTION
    assert "Xperiencia" in STATIC_INSTRUCTION
    assert "submit_lead_qualification" not in STATIC_INSTRUCTION
    assert "request_human_handoff" not in STATIC_INSTRUCTION
    assert "{{" not in STATIC_INSTRUCTION


def test_static_instruction_confirm_before_handoff_protocol() -> None:
    text = STATIC_INSTRUCTION.lower()
    assert "elegir un rango de la lista" in text
    assert "pregunta **una vez**" in text or "pregunta una vez" in text
    assert "no reutilices" in text
    assert "grupo o fecha a medida" in text
    assert "no improvises asesor" in text
    assert "no inventes si el plan es apto" in text
    assert "sí esa fecha" not in text


def test_build_instruction_omits_bridge_example() -> None:
    ctx = _FakeReadonlyContext({})
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]
    assert "Ejemplo de respuesta tras handoff" not in text
    assert "qualification_score" not in text


def test_build_instruction_includes_ctwa_block_when_state_set() -> None:
    ctx = _FakeReadonlyContext(
        {
            "ctwa_ad_body": "Tour de avistamiento de ballenas en Nuquí",
            "ctwa_plan_hint": "Bienvenido al tour de ballenas",
        }
    )
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "Origen CTWA" in text
    assert "Tour de avistamiento de ballenas en Nuquí" in text
    assert "Bienvenido al tour de ballenas" in text
    assert "search_context" in text


def test_build_instruction_omits_ctwa_block_when_handled() -> None:
    ctx = _FakeReadonlyContext(
        {
            "ctwa_ad_body": "Tour de avistamiento de ballenas en Nuquí",
            "ctwa_plan_hint": "Bienvenido al tour de ballenas",
            "ctwa_handled": "true",
        }
    )
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "Origen CTWA" not in text
    assert "Tour de avistamiento de ballenas en Nuquí" not in text


def test_static_instruction_groups_and_lists_matching_plans() -> None:
    text = STATIC_INSTRUCTION.lower()
    assert "ya agrupa por plan" in text
    assert "misma ficha dos veces" in text
    assert "primer bloque" in text
    assert "explore=true" in text
    assert "plan_focus" in text
    assert "ignora `artifact`" in text
    assert "pregunta exploratoria" in text
    assert "ficha es de lo pedido" in text
    assert "paso, escala o zona cercana" in text
    assert "no hay planes publicados" in text
    assert "otro plan" in text
    assert "2\u20133 datos" not in text
    assert "2-3 datos" not in text
    assert "máx. 4 viñetas" not in text
    assert "max. 4 viñetas" not in text
    assert "máx. 2 bloques" not in text
    assert "tolima" not in text
    assert "nuquí" not in text
    assert "nuqui" not in text
    assert "agosto" not in text


def test_static_instruction_plan_activo_and_vague_choice() -> None:
    text = STATIC_INSTRUCTION.lower()
    assert "plan ya identificado" in text
    assert "no reabras" in text
    assert "pregunta cuál" in text
    assert "no asumas el homónimo" in text


def test_static_instruction_extra_search_when_uncovered() -> None:
    text = STATIC_INSTRUCTION.lower()
    assert "consulta extra" in text
    assert "otra query" in text
    assert "nunca una tercera" in text
    assert "una sola vez" not in text
    assert "1 llamada por turno" not in text


def test_static_instruction_compare_only_listed_plans() -> None:
    text = STATIC_INSTRUCTION.lower()
    assert "solo los planes ya listados" in text
    assert "no inventes un tour" in text


def test_static_instruction_ficha_no_disponible_and_no_raw_url() -> None:
    text = STATIC_INSTRUCTION.lower()
    assert "ficha_no_disponible" in text
    assert "no llames `explore`" in text or "no llames explore" in text
    assert "url cruda" in text
    assert "completar" in text


def test_static_instruction_ctwa_product_vs_family() -> None:
    text = STATIC_INSTRUCTION.lower()
    assert "un producto" in text
    assert "familia" in text
    assert "qué te interesa" in text


def test_build_instruction_omits_ctwa_block_without_ad_body() -> None:
    ctx = _FakeReadonlyContext(
        {
            "ctwa_plan_hint": "ignored without ad body",
        }
    )
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "Origen CTWA" not in text
    assert "ignored without ad body" not in text
