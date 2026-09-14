"""Tests for bridge sub-agent instruction bundle."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

from app.subagents.bridge.agent import bridge_agent
from app.subagents.bridge.instructions import STATIC_INSTRUCTION, build_instruction


class _FakeReadonlyContext:
    def __init__(
        self,
        state: dict[str, Any],
        session_id: str | None = "conv-test",
    ) -> None:
        self.state = state
        self.session = type("S", (), {"id": session_id})() if session_id else None


def test_bridge_agent_config() -> None:
    assert bridge_agent.name == "bridge"
    assert bridge_agent.model == "gemini-flash-lite-latest"
    assert bridge_agent.tools == []


def test_static_instruction_includes_handoff_rules() -> None:
    assert "Amaru" in STATIC_INSTRUCTION
    assert "handoff" in STATIC_INSTRUCTION.lower()
    assert "{{" not in STATIC_INSTRUCTION


def test_build_instruction_renders_bridge_example_and_reason() -> None:
    with patch(
        "chatty_agent_common.instructions.resolve_handoff_bridge_message",
        return_value="Te conecto con Laura del equipo.",
    ):
        ctx = _FakeReadonlyContext(
            {"handoff_reason": "Plan y fecha confirmados para reserva."}
        )
        text = asyncio.run(build_instruction(ctx))  # type: ignore[arg-type]

    assert "Plan y fecha confirmados para reserva." in text
    assert "Te conecto con Laura del equipo." in text
    assert "Ejemplo de tono" in text
    assert "search_context" not in text
