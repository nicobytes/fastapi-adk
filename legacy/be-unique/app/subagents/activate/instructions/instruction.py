"""Activate instruction bundle: static rules + dynamic stage/note."""

from __future__ import annotations

import pathlib

from chatty_agent_common.instructions import load_agent_instructions

__all__ = [
    "STATIC_INSTRUCTION",
    "build_instruction",
]

_bundle = load_agent_instructions(
    pathlib.Path(__file__).parent,
    session_keys=("activate_stage", "activate_note"),
)

STATIC_INSTRUCTION = _bundle.static_instruction
build_instruction = _bundle.build_instruction
