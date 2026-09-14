"""Bridge instruction bundle: static rules + dynamic handoff example."""

from __future__ import annotations

import pathlib

from app.qualification import DEFAULT_BRIDGE
from chatty_agent_common.instructions import load_agent_instructions

__all__ = [
    "STATIC_INSTRUCTION",
    "build_instruction",
]

_bundle = load_agent_instructions(
    pathlib.Path(__file__).parent,
    session_keys=("handoff_reason",),
    default_bridge=DEFAULT_BRIDGE,
    include_bridge_example=True,
)

STATIC_INSTRUCTION = _bundle.static_instruction
build_instruction = _bundle.build_instruction
