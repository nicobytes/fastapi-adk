"""Load ADK static/dynamic instruction markdown bundles for Chatty agents.

Convention under ``app/instructions/``:

- ``personality.md`` (required) — identity / tone → ``static_instruction``
- ``instructions.md`` (required) — operating protocol → ``static_instruction``
- ``session.md`` (optional) — Jinja template for per-turn dynamic ``instruction``

When ``session.md`` is absent, ``build_instruction`` returns an empty string
(ADK keeps only ``static_instruction`` in ``system_instruction``).
"""

from __future__ import annotations

import pathlib
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from google.adk.agents.readonly_context import ReadonlyContext
from jinja2.sandbox import SandboxedEnvironment

from chatty_agent_common.handoff import resolve_handoff_bridge_message

__all__ = [
    "AgentInstructions",
    "load_agent_instructions",
]

_PERSONALITY = "personality.md"
_INSTRUCTIONS = "instructions.md"
_SESSION = "session.md"

_ENV = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)

InstructionProvider = Callable[[ReadonlyContext], Awaitable[str]]
ExtraSessionVars = Callable[[ReadonlyContext], Mapping[str, Any]]


@dataclass(frozen=True)
class AgentInstructions:
    """ADK-ready instruction bundle loaded from a tenant ``instructions/`` dir."""

    static_instruction: str
    build_instruction: InstructionProvider
    card_instruction: str


def _read_required(directory: pathlib.Path, name: str) -> str:
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing required instruction file: {path}. "
            f"Expected {_PERSONALITY} and {_INSTRUCTIONS} under {directory}."
        )
    return path.read_text(encoding="utf-8")


def _read_optional(directory: pathlib.Path, name: str) -> str | None:
    path = directory / name
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _session_id(ctx: ReadonlyContext) -> str | None:
    session = getattr(ctx, "session", None)
    if session is None:
        return None
    session_id = getattr(session, "id", None)
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None


def _state_vars(
    state: Mapping[str, Any], session_keys: Sequence[str]
) -> dict[str, str]:
    return {key: str(state.get(key) or "") for key in session_keys}


def _resolve_bridge(ctx: ReadonlyContext, *, default_bridge: str) -> str:
    cid = _session_id(ctx)
    if not cid:
        return default_bridge
    return resolve_handoff_bridge_message(cid, default=default_bridge)


def load_agent_instructions(
    directory: pathlib.Path | str,
    *,
    session_keys: Sequence[str] = (),
    default_bridge: str = "",
    include_bridge_example: bool = False,
    extra_session_vars: ExtraSessionVars | None = None,
) -> AgentInstructions:
    """Load markdown bundle and wire ADK static vs dynamic providers.

    Args:
        directory: Path to the agent's ``instructions/`` folder.
        session_keys: State keys injected into ``session.md`` (empty string if unset).
        default_bridge: Fallback when CRM/env have no handoff bridge copy.
        include_bridge_example: When True and ``session.md`` exists, resolve
            ``handoff_bridge_example`` via CRM → env → ``default_bridge``.
        extra_session_vars: Optional per-turn extras (e.g. ``current_date``).
    """
    root = pathlib.Path(directory)
    personality = _read_required(root, _PERSONALITY)
    instructions = _read_required(root, _INSTRUCTIONS)
    static_instruction = f"{personality.rstrip()}\n\n{instructions.lstrip()}"

    session_template = _read_optional(root, _SESSION)
    keys = tuple(session_keys)

    if session_template is None:

        async def build_instruction(_ctx: ReadonlyContext) -> str:
            return ""

        return AgentInstructions(
            static_instruction=static_instruction,
            build_instruction=build_instruction,
            card_instruction=static_instruction,
        )

    compiled = _ENV.from_string(session_template)

    def _render(ctx: ReadonlyContext) -> str:
        state = dict(ctx.state)
        vars_: dict[str, Any] = _state_vars(state, keys)
        if include_bridge_example:
            vars_["handoff_bridge_example"] = _resolve_bridge(
                ctx, default_bridge=default_bridge
            )
        if extra_session_vars is not None:
            vars_.update(dict(extra_session_vars(ctx)))
        return compiled.render(**vars_)

    async def build_instruction(ctx: ReadonlyContext) -> str:
        return _render(ctx)

    empty_ctx = SimpleNamespace(state={}, session=None)
    card_instruction = f"{static_instruction.rstrip()}\n\n{_render(empty_ctx)}"  # type: ignore[arg-type]

    return AgentInstructions(
        static_instruction=static_instruction,
        build_instruction=build_instruction,
        card_instruction=card_instruction,
    )
