"""Sofía instruction bundle: static personality/rules + dynamic session."""

from __future__ import annotations

import pathlib
from datetime import datetime
from zoneinfo import ZoneInfo

from google.adk.agents.readonly_context import ReadonlyContext

from chatty_agent_common.instructions import load_agent_instructions

__all__ = [
    "CARD_INSTRUCTION",
    "STATIC_INSTRUCTION",
    "build_instruction",
]

_TZ_LA_PAZ = ZoneInfo("America/La_Paz")
_WEEKDAYS_ES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)

_SESSION_KEYS = (
    "active_sede",
    "customer_name",
    "active_service_name",
    "active_duration_minutes",
    "last_booking_id",
    "last_booking_label",
    "qualification_score",
    "lead_qualifies",
    "ctwa_ad_body",
    "ctwa_plan_hint",
    "ctwa_handled",
)


def _la_paz_date_vars(_ctx: ReadonlyContext) -> dict[str, str]:
    now = datetime.now(_TZ_LA_PAZ)
    return {
        "current_date": now.date().isoformat(),
        "current_weekday_es": _WEEKDAYS_ES[now.weekday()],
    }


_bundle = load_agent_instructions(
    pathlib.Path(__file__).parent,
    session_keys=_SESSION_KEYS,
    include_bridge_example=False,
    extra_session_vars=_la_paz_date_vars,
)

STATIC_INSTRUCTION = _bundle.static_instruction
build_instruction = _bundle.build_instruction
CARD_INSTRUCTION = _bundle.card_instruction
