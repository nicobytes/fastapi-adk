"""Tests for activate sub-agent instruction bundle."""

from __future__ import annotations

import asyncio
from typing import Any

from app.subagents.activate.agent import activate_agent
from app.subagents.activate.instructions import STATIC_INSTRUCTION, build_instruction


class _FakeReadonlyContext:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.session = type("S", (), {"id": "conv-test"})()


def test_activate_agent_config() -> None:
    assert activate_agent.name == "activate"
    assert activate_agent.model == "gemini-flash-lite-latest"
    assert activate_agent.tools == []


def test_static_instruction_includes_activate_rules() -> None:
    assert "Sofía" in STATIC_INSTRUCTION
    assert "inactividad" in STATIC_INSTRUCTION.lower()
    assert "{{" not in STATIC_INSTRUCTION


def test_build_instruction_renders_stage_and_note() -> None:
    ctx = _FakeReadonlyContext(
        {
            "activate_stage": "first_contact",
            "activate_note": "Invite a continuar la conversación.",
        }
    )
    text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "first_contact" in text
    assert "Invite a continuar la conversación." in text
    assert "search_context" not in text
