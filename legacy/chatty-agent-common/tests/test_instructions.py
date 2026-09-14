"""Tests for load_agent_instructions markdown bundle loader."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from chatty_agent_common.instructions import load_agent_instructions


class _FakeCtx:
    def __init__(
        self,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        self.state = state or {}
        self.session = type("S", (), {"id": session_id})() if session_id else None


def _write_bundle(
    tmp_path: Path,
    *,
    personality: str = "# Persona\nSoy el agente.",
    instructions: str = "# Rules\nSigue el protocolo.",
    session: str | None = None,
) -> Path:
    (tmp_path / "personality.md").write_text(personality, encoding="utf-8")
    (tmp_path / "instructions.md").write_text(instructions, encoding="utf-8")
    if session is not None:
        (tmp_path / "session.md").write_text(session, encoding="utf-8")
    return tmp_path


def test_missing_personality_raises(tmp_path: Path) -> None:
    (tmp_path / "instructions.md").write_text("rules", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match=r"personality\.md"):
        load_agent_instructions(tmp_path)


def test_missing_instructions_raises(tmp_path: Path) -> None:
    (tmp_path / "personality.md").write_text("persona", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match=r"instructions\.md"):
        load_agent_instructions(tmp_path)


def test_static_only_no_session(tmp_path: Path) -> None:
    _write_bundle(tmp_path)
    with patch(
        "chatty_agent_common.instructions.resolve_handoff_bridge_message"
    ) as resolve:
        bundle = load_agent_instructions(tmp_path)
        text = asyncio.run(bundle.build_instruction(_FakeCtx()))  # type: ignore[arg-type]
        assert text == ""
        resolve.assert_not_called()

    assert "Soy el agente" in bundle.static_instruction
    assert "Sigue el protocolo" in bundle.static_instruction
    assert "{{" not in bundle.static_instruction
    assert bundle.card_instruction == bundle.static_instruction
    assert bundle.card_instruction


def test_session_keys_and_bridge_example(tmp_path: Path) -> None:
    _write_bundle(
        tmp_path,
        session=(
            "## Estado\n"
            "- score: {{ qualification_score }}\n\n"
            "## Ejemplo de respuesta tras handoff\n\n"
            "{{ handoff_bridge_example }}\n"
        ),
    )
    with patch(
        "chatty_agent_common.instructions.resolve_handoff_bridge_message",
        return_value="Bridge CRM",
    ) as resolve:
        bundle = load_agent_instructions(
            tmp_path,
            session_keys=("qualification_score",),
            default_bridge="Bridge default",
            include_bridge_example=True,
        )
        text = asyncio.run(
            bundle.build_instruction(
                _FakeCtx(state={"qualification_score": "80"}, session_id="conv-1")
            )  # type: ignore[arg-type]
        )
        resolve.assert_called_once_with("conv-1", default="Bridge default")

    assert "score: 80" in text
    assert "Bridge CRM" in text
    assert "Ejemplo de respuesta tras handoff" in text
    assert "{{" not in bundle.static_instruction
    assert "Bridge default" in bundle.card_instruction


def test_session_without_bridge_skips_resolve(tmp_path: Path) -> None:
    _write_bundle(
        tmp_path,
        session="- score: {{ qualification_score }}\n",
    )
    with patch(
        "chatty_agent_common.instructions.resolve_handoff_bridge_message"
    ) as resolve:
        bundle = load_agent_instructions(
            tmp_path,
            session_keys=("qualification_score",),
            include_bridge_example=False,
        )
        text = asyncio.run(
            bundle.build_instruction(_FakeCtx(state={"qualification_score": "10"}))
        )  # type: ignore[arg-type]
        resolve.assert_not_called()
    assert "score: 10" in text


def test_extra_session_vars(tmp_path: Path) -> None:
    _write_bundle(
        tmp_path,
        session="date: {{ current_date }}\n",
    )

    def extras(_ctx: Any) -> dict[str, str]:
        return {"current_date": "2026-08-07"}

    bundle = load_agent_instructions(
        tmp_path,
        extra_session_vars=extras,
    )
    text = asyncio.run(bundle.build_instruction(_FakeCtx()))  # type: ignore[arg-type]
    assert "date: 2026-08-07" in text
