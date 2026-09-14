"""Customer instruction bundle: static personality/rules + dynamic session."""

from __future__ import annotations

import pathlib

from chatty_agent_common.instructions import load_agent_instructions

__all__ = [
    "CARD_INSTRUCTION",
    "STATIC_INSTRUCTION",
    "build_instruction",
]

_bundle = load_agent_instructions(
    pathlib.Path(__file__).parent,
    session_keys=(
        "ctwa_ad_body",
        "ctwa_plan_hint",
        "ctwa_handled",
    ),
)

STATIC_INSTRUCTION = _bundle.static_instruction
build_instruction = _bundle.build_instruction
CARD_INSTRUCTION = _bundle.card_instruction
