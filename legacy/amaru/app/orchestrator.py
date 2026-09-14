"""Amaru BaseAgent orchestrator: qualifier → Python handoff → bridge | customer."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from typing import Any

from google.adk.agents import Agent, BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
from pydantic import Field

from app.qualification import (
    apply_bant_signals,
    handoff_reason,
    maybe_execute_handoff,
    parse_bant_signals,
    should_bypass_turn_gate,
)
from app.subagents.activate.agent import activate_agent
from app.subagents.bridge.agent import bridge_agent
from app.subagents.customer.agent import customer_agent
from app.subagents.qualifier.agent import qualifier_agent
from chatty_agent_common.adk_events import (
    CLEAR_ACTIVATE_STATE,
    ensure_invocation_id,
    model_text_event,
    state_delta_event,
)

logger = logging.getLogger(__name__)


def _session_id(ctx: InvocationContext) -> str | None:
    session = ctx.session
    session_id = getattr(session, "id", None)
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None


def _handoff_reason(criteria: dict[str, Any]) -> str:
    return handoff_reason(criteria)


def _model_text(event: Event) -> str | None:
    content = event.content
    if content is None or not content.parts:
        return None
    part = content.parts[0]
    text = getattr(part, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


def _is_activate_pending(state: Mapping[str, Any]) -> bool:
    return str(state.get("activate_pending") or "").lower() == "true"


def _clear_activate_state(state: dict[str, Any]) -> None:
    state.update(CLEAR_ACTIVATE_STATE)


class AmaruOrchestrator(BaseAgent):
    """Runs BANT classification each turn; handoff in Python or delegates to customer."""

    qualifier: Agent = Field(description="Silent BANT classifier sub-agent.")
    bridge: Agent = Field(description="Handoff bridge message composer sub-agent.")
    activate: Agent = Field(description="Inactivity nudge composer sub-agent.")
    customer: Agent = Field(description="Customer-facing chat sub-agent.")

    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        if _is_activate_pending(state):
            async for event in self._stream_activate(ctx):
                yield event
            _clear_activate_state(state)
            return

        conversation_id = _session_id(ctx)
        qualifier_ok = False

        try:
            await self._run_qualifier(ctx)
            qualifier_ok = True
        except Exception:
            logger.exception("Qualifier failed; falling back to customer")

        if qualifier_ok:
            criteria = parse_bant_signals(state.get("bant_result"))
            if criteria is not None:
                score_result = apply_bant_signals(
                    state=state,
                    conversation_id=conversation_id,
                    criteria=criteria,
                )
                handoff = maybe_execute_handoff(
                    state=state,
                    conversation_id=conversation_id,
                    reason=_handoff_reason(criteria),
                    qualifies=bool(score_result["qualifies"]),
                    score=int(score_result["score"]),
                    explicit_human_request=should_bypass_turn_gate(criteria),
                )
                if handoff.get("status") == "WAITING_HUMAN":
                    fallback_bridge = str(handoff.get("bridge_message") or "")
                    state["handoff_reason"] = _handoff_reason(criteria)
                    async for event in self._stream_handoff_bridge(
                        ctx,
                        fallback_bridge=fallback_bridge,
                    ):
                        yield event
                    return

        async for event in self._stream_customer(ctx):
            yield event
        self._mark_ctwa_handled(state)

    async def _run_qualifier(self, ctx: InvocationContext) -> None:
        """Run silent BANT classifier; merge state_delta without yielding to stream."""
        async for event in self.qualifier.run_async(ctx):
            actions = getattr(event, "actions", None)
            delta = getattr(actions, "state_delta", None) if actions else None
            if isinstance(delta, dict):
                ctx.session.state.update(delta)

    def _mark_ctwa_handled(self, state: dict[str, Any]) -> None:
        if state.get("ctwa_ad_body") and not state.get("ctwa_handled"):
            state["ctwa_handled"] = "true"

    async def _stream_activate(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        """Yield a short nudge from the activate agent (Nest scheduler path)."""
        got_text = False
        try:
            async for event in self.activate.run_async(ctx):
                text = _model_text(event)
                if text is None:
                    continue
                got_text = True
                yield model_text_event(
                    ctx,
                    text,
                    author=self.name,
                    state=CLEAR_ACTIVATE_STATE,
                )
        except Exception:
            logger.exception("Activate agent failed")

        if not got_text:
            yield state_delta_event(
                ctx,
                author=self.name,
                state=CLEAR_ACTIVATE_STATE,
            )

    async def _stream_handoff_bridge(
        self,
        ctx: InvocationContext,
        *,
        fallback_bridge: str,
    ) -> AsyncGenerator[Event, None]:
        """Yield a personalized bridge from the bridge agent, or deterministic fallback."""
        got_text = False
        try:
            async for event in self.bridge.run_async(ctx):
                text = _model_text(event)
                if text is None:
                    continue
                got_text = True
                yield model_text_event(ctx, text, author=self.name)
        except Exception:
            logger.exception("Bridge agent failed; using deterministic fallback")

        if got_text:
            return

        if fallback_bridge.strip():
            yield model_text_event(
                ctx,
                fallback_bridge.strip(),
                author=self.name,
            )

    async def _stream_customer(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        async for event in self.customer.run_async(ctx):
            yield ensure_invocation_id(event, ctx)


def create_amaru_orchestrator(
    *,
    before_agent_callback: Sequence[Callable[[CallbackContext], types.Content | None]]
    | None = None,
    after_agent_callback: Callable[[CallbackContext], types.Content | None]
    | None = None,
) -> AmaruOrchestrator:
    """Factory to avoid ADK parent-agent registration issues at import time."""
    qualifier = qualifier_agent
    bridge = bridge_agent
    activate = activate_agent
    customer = customer_agent
    return AmaruOrchestrator(
        name="amaru",
        description=(
            "Xperiencia WhatsApp orchestrator: BANT via qualifier, "
            "Python handoff, bridge or customer chat."
        ),
        qualifier=qualifier,
        bridge=bridge,
        activate=activate,
        customer=customer,
        sub_agents=[qualifier, bridge, activate, customer],
        before_agent_callback=list(before_agent_callback or []),
        after_agent_callback=after_agent_callback,
    )
