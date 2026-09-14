"""Amaru root agent — BaseAgent orchestrator + customer/qualifier sub-agents."""

from __future__ import annotations

from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App

from app.callbacks import recover_unknown_tool_error, seed_session_state
from app.orchestrator import create_amaru_orchestrator
from app.qualification import HANDOFF_SOURCE
from app.subagents.customer.instructions import (
    CARD_INSTRUCTION,
    STATIC_INSTRUCTION,
    build_instruction,
)
from app.subagents.customer.tools.search_context import _ORG_SLUG
from chatty_agent_common.outbound import mirror_outbound_for_playground
from chatty_agent_common.playground_session import (
    make_ensure_playground_conversation_callback,
)

__all__ = [
    "CARD_INSTRUCTION",
    "HANDOFF_SOURCE",
    "STATIC_INSTRUCTION",
    "app",
    "build_instruction",
    "recover_unknown_tool_error",
    "root_agent",
]


root_agent = create_amaru_orchestrator(
    before_agent_callback=[
        make_ensure_playground_conversation_callback(_ORG_SLUG),
        seed_session_state,
    ],
    after_agent_callback=mirror_outbound_for_playground,
)

app = App(
    root_agent=root_agent,
    name="app",
    context_cache_config=ContextCacheConfig(
        ttl_seconds=3600,
        cache_intervals=10,
        min_tokens=2048,
    ),
)
