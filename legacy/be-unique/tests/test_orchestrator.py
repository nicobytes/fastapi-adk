"""Unit tests for BeUniqueOrchestrator routing (no Vertex)."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.genai import types

from app.agent import root_agent


@pytest.fixture(autouse=True)
def _mock_persist_qualification_snapshot() -> Iterator[None]:
    with patch(
        "chatty_agent_common.qualification.persist_conversation_qualification_snapshot"
    ):
        yield


class _FakeSession:
    def __init__(self, state: dict[str, Any], session_id: str = "conv-orch-1") -> None:
        self.state = state
        self.id = session_id


def _fake_ctx(state: dict[str, Any] | None = None) -> InvocationContext:
    ctx = MagicMock(spec=InvocationContext)
    ctx.session = _FakeSession(state if state is not None else {})
    ctx.invocation_id = "inv-test"
    ctx.branch = None
    return ctx


def _model_event(text: str, *, author: str = "customer") -> Event:
    return Event(
        author=author,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


def _event_text(event: Event) -> str:
    content = event.content
    assert content is not None
    parts = content.parts
    assert parts is not None
    text = parts[0].text
    assert text is not None
    return text


def _bant_json(**overrides: Any) -> str:
    payload = {
        "interest_level": "High",
        "budget_status": "Aligned",
        "purchase_urgency": "ShortTerm",
        "has_decision_authority": True,
        "explicit_human_request": False,
        "plan_and_date_confirmed": False,
    }
    payload.update(overrides)
    return json.dumps(payload)


async def _events(*items: Event) -> AsyncGenerator[Event, None]:
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_high_score_without_explicit_human_runs_customer() -> None:
    """Be Unique: score/plan+date never trigger handoff without explicit human."""
    state = {"user_turn_count": 2}
    ctx = _fake_ctx(state)
    state["bant_result"] = json.loads(
        _bant_json(plan_and_date_confirmed=True, has_decision_authority=False)
    )

    async def _noop_qualifier(_ctx: InvocationContext) -> None:
        return None

    async def _customer_stream(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event("Continuemos con su cita.")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=_noop_qualifier),
        patch.object(root_agent, "_stream_customer", side_effect=_customer_stream),
        patch.object(root_agent, "_stream_handoff_bridge") as stream_bridge,
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={"status": "rejected", "message": "no explicit human"},
        ),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert len(events) == 1
    assert _event_text(events[0]) == "Continuemos con su cita."
    stream_bridge.assert_not_called()


@pytest.mark.asyncio
async def test_customer_stream_marks_ctwa_handled() -> None:
    state: dict[str, Any] = {
        "user_turn_count": 1,
        "ctwa_ad_body": "Hidrafacial",
    }
    ctx = _fake_ctx(state)
    state["bant_result"] = json.loads(_bant_json())

    async def _noop_qualifier(_ctx: InvocationContext) -> None:
        return None

    async def _customer_stream(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event("¿En cuál sede desea atenderse?")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=_noop_qualifier),
        patch.object(root_agent, "_stream_customer", side_effect=_customer_stream),
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={"status": "rejected", "message": "no explicit human"},
        ),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert len(events) == 1
    assert state["ctwa_handled"] == "true"


@pytest.mark.asyncio
async def test_turn1_without_explicit_human_runs_customer() -> None:
    state = {"user_turn_count": 1}
    ctx = _fake_ctx(state)
    state["bant_result"] = json.loads(_bant_json())

    async def _noop_qualifier(_ctx: InvocationContext) -> None:
        return None

    async def _customer_stream(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event("Hola, ¿en qué le ayudo?")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=_noop_qualifier),
        patch.object(root_agent, "_stream_customer", side_effect=_customer_stream),
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={"status": "rejected", "message": "too early"},
        ),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert len(events) == 1
    assert _event_text(events[0]) == "Hola, ¿en qué le ayudo?"


@pytest.mark.asyncio
async def test_explicit_human_turn1_handoff_without_customer() -> None:
    state = {"user_turn_count": 1}
    ctx = _fake_ctx(state)
    state["bant_result"] = json.loads(_bant_json(explicit_human_request=True))
    bridge = "Le paso con un asesor."

    async def _noop_qualifier(_ctx: InvocationContext) -> None:
        return None

    async def _bridge_stream(
        _ctx: InvocationContext,
        *,
        fallback_bridge: str,
    ) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event(fallback_bridge, author="be_unique")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=_noop_qualifier),
        patch.object(root_agent, "_stream_customer") as stream_customer,
        patch.object(root_agent, "_stream_handoff_bridge", side_effect=_bridge_stream),
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={
                "status": "WAITING_HUMAN",
                "bridge_message": bridge,
                "score": 100,
            },
        ),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert len(events) == 1
    assert _event_text(events[0]) == bridge
    stream_customer.assert_not_called()


@pytest.mark.asyncio
async def test_explicit_human_turn2_handoff_only_bridge() -> None:
    state = {"user_turn_count": 2}
    ctx = _fake_ctx(state)
    state["bant_result"] = json.loads(_bant_json(explicit_human_request=True))
    bridge = "Un momento, le conecto con un asesor."

    async def _noop_qualifier(_ctx: InvocationContext) -> None:
        return None

    async def _bridge_stream(
        _ctx: InvocationContext,
        *,
        fallback_bridge: str,
    ) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event(fallback_bridge, author="be_unique")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=_noop_qualifier),
        patch.object(root_agent, "_stream_customer") as stream_customer,
        patch.object(root_agent, "_stream_handoff_bridge", side_effect=_bridge_stream),
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={
                "status": "WAITING_HUMAN",
                "bridge_message": bridge,
                "score": 100,
            },
        ),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert len(events) == 1
    assert _event_text(events[0]) == bridge
    stream_customer.assert_not_called()


@pytest.mark.asyncio
async def test_qualifier_failure_runs_customer() -> None:
    ctx = _fake_ctx({"user_turn_count": 1})

    async def _failing_qualifier(_ctx: InvocationContext) -> None:
        raise RuntimeError("qualifier down")

    async def _customer_stream(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event("Respuesta de respaldo.")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=_failing_qualifier),
        patch.object(root_agent, "_stream_customer", side_effect=_customer_stream),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert len(events) == 1
    assert _event_text(events[0]) == "Respuesta de respaldo."


@pytest.mark.asyncio
async def test_qualifier_bant_json_not_yielded() -> None:
    state = {"user_turn_count": 1}
    ctx = _fake_ctx(state)
    bant_text = _bant_json()
    state["bant_result"] = json.loads(bant_text)

    async def _noop_qualifier(_ctx: InvocationContext) -> None:
        return None

    async def _customer_stream(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event("Visible al usuario.")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=_noop_qualifier),
        patch.object(root_agent, "_stream_customer", side_effect=_customer_stream),
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={"status": "rejected", "message": "too early"},
        ),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert all(
        not (
            event.content
            and event.content.parts
            and event.content.parts[0].text == bant_text
        )
        for event in events
    )
    assert _event_text(events[0]) == "Visible al usuario."


@pytest.mark.asyncio
async def test_handoff_sets_reason_before_bridge_stream() -> None:
    state = {"user_turn_count": 2}
    ctx = _fake_ctx(state)
    state["bant_result"] = json.loads(_bant_json(explicit_human_request=True))
    bridge = "Perfecto, le conecto con un asesor de Be Unique."

    async def _noop_qualifier(_ctx: InvocationContext) -> None:
        return None

    async def _bridge_stream(
        _ctx: InvocationContext,
        *,
        fallback_bridge: str,
    ) -> AsyncGenerator[Event, None]:
        assert state["handoff_reason"] == "Cliente solicitó atención humana."
        async for event in _events(_model_event(bridge, author="be_unique")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=_noop_qualifier),
        patch.object(root_agent, "_stream_customer") as stream_customer,
        patch.object(root_agent, "_stream_handoff_bridge", side_effect=_bridge_stream),
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={
                "status": "WAITING_HUMAN",
                "bridge_message": "fallback",
                "score": 100,
            },
        ),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert len(events) == 1
    assert _event_text(events[0]) == bridge
    stream_customer.assert_not_called()


@pytest.mark.asyncio
async def test_stream_handoff_bridge_falls_back_when_bridge_empty() -> None:
    ctx = _fake_ctx({})
    fallback = "Un momento, le estoy conectando con un asesor del equipo."

    async def _empty_bridge(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        if False:
            yield _model_event("never")

    mock_bridge = MagicMock()
    mock_bridge.run_async = _empty_bridge
    original_bridge = root_agent.bridge
    root_agent.bridge = mock_bridge
    try:
        events = [
            event
            async for event in root_agent._stream_handoff_bridge(
                ctx,
                fallback_bridge=fallback,
            )
        ]
    finally:
        root_agent.bridge = original_bridge

    assert len(events) == 1
    assert events[0].author == "be_unique"
    assert events[0].invocation_id == "inv-test"
    assert _event_text(events[0]) == fallback


@pytest.mark.asyncio
async def test_qualifier_state_delta_applied_without_preseed() -> None:
    state: dict[str, Any] = {"user_turn_count": 2}
    ctx = _fake_ctx(state)
    bant = json.loads(_bant_json(explicit_human_request=True))
    bridge = "Le conecto con un asesor."

    async def _qualifier_stream(
        _ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        yield Event(
            author="qualifier",
            actions=EventActions(state_delta={"bant_result": bant}),
        )

    async def _bridge_stream(
        _ctx: InvocationContext,
        *,
        fallback_bridge: str,
    ) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event(fallback_bridge, author="be_unique")):
            yield event

    mock_qualifier = MagicMock()
    mock_qualifier.run_async = _qualifier_stream
    original_qualifier = root_agent.qualifier
    root_agent.qualifier = mock_qualifier
    try:
        with (
            patch.object(root_agent, "_stream_customer") as stream_customer,
            patch.object(
                root_agent, "_stream_handoff_bridge", side_effect=_bridge_stream
            ),
            patch(
                "app.orchestrator.maybe_execute_handoff",
                return_value={
                    "status": "WAITING_HUMAN",
                    "bridge_message": bridge,
                    "score": 100,
                },
            ),
        ):
            events = [event async for event in root_agent._run_async_impl(ctx)]
    finally:
        root_agent.qualifier = original_qualifier

    assert state["bant_result"] == bant
    assert len(events) == 1
    assert _event_text(events[0]) == bridge
    stream_customer.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("activate_stage", ["first_contact", "in_conversation"])
async def test_activate_pending_runs_activate_only_and_clears_state(
    activate_stage: str,
) -> None:
    state = {
        "user_turn_count": 2,
        "activate_pending": "true",
        "activate_stage": activate_stage,
        "activate_note": "Retome el tratamiento pendiente.",
    }
    ctx = _fake_ctx(state)
    nudge = "¿Seguimos con su valoración en Sucre?"

    async def _activate_stream(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event(nudge, author="be_unique")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier") as run_qualifier,
        patch.object(root_agent, "_stream_customer") as stream_customer,
        patch.object(root_agent, "_stream_activate", side_effect=_activate_stream),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    assert len(events) == 1
    assert events[0].author == "be_unique"
    assert _event_text(events[0]) == nudge
    run_qualifier.assert_not_called()
    stream_customer.assert_not_called()
    assert state["activate_pending"] == ""
    assert state["activate_stage"] == ""
    assert state["activate_note"] == ""


@pytest.mark.asyncio
async def test_activate_cleared_state_runs_customer_next_turn() -> None:
    state = {
        "user_turn_count": 1,
        "activate_pending": "",
        "activate_stage": "",
        "activate_note": "",
    }
    ctx = _fake_ctx(state)

    async def _customer_stream(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event("¿En qué sede la vemos?")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=lambda _ctx: None),
        patch.object(root_agent, "_stream_activate") as stream_activate,
        patch.object(root_agent, "_stream_customer", side_effect=_customer_stream),
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={"status": "rejected", "message": "too early"},
        ),
    ):
        events = [event async for event in root_agent._run_async_impl(ctx)]

    stream_activate.assert_not_called()
    assert _event_text(events[0]) == "¿En qué sede la vemos?"


@pytest.mark.asyncio
@pytest.mark.parametrize("activate_stage", ["first_contact", "in_conversation"])
async def test_activate_nudge_then_user_reply_runs_customer(
    activate_stage: str,
) -> None:
    """Vertex rebuilds session.state from event state_delta, not in-memory pops.

    Playground loop: nudge, user replies, same nudge again while
    activate_pending stayed \"true\".
    """
    persisted = {
        "user_turn_count": 1,
        "activate_pending": "true",
        "activate_stage": activate_stage,
        "activate_note": "Retome el tratamiento pendiente.",
    }
    ctx = _fake_ctx(dict(persisted))
    nudge = "¿Todo bien por ahí?"

    async def _activate_agent(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield _model_event(nudge, author="activate")

    mock_activate = MagicMock()
    mock_activate.run_async = _activate_agent
    original = root_agent.activate
    root_agent.activate = mock_activate
    try:
        events = [event async for event in root_agent._run_async_impl(ctx)]
    finally:
        root_agent.activate = original

    assert _event_text(events[0]) == nudge

    rebuilt = dict(persisted)
    for event in events:
        rebuilt.update(getattr(event.actions, "state_delta", None) or {})
    assert rebuilt["activate_pending"] == ""
    assert rebuilt["activate_stage"] == ""
    assert rebuilt["activate_note"] == ""

    ctx2 = _fake_ctx(rebuilt)

    async def _customer_stream(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in _events(_model_event("¿En qué sede la vemos?")):
            yield event

    with (
        patch.object(root_agent, "_run_qualifier", side_effect=lambda _ctx: None),
        patch.object(root_agent, "_stream_activate") as stream_activate,
        patch.object(root_agent, "_stream_customer", side_effect=_customer_stream),
        patch(
            "app.orchestrator.maybe_execute_handoff",
            return_value={"status": "rejected", "message": "too early"},
        ),
    ):
        events2 = [event async for event in root_agent._run_async_impl(ctx2)]

    stream_activate.assert_not_called()
    assert _event_text(events2[0]) == "¿En qué sede la vemos?"


@pytest.mark.asyncio
@pytest.mark.parametrize("activate_stage", ["first_contact", "in_conversation"])
async def test_stream_activate_copies_invocation_id(activate_stage: str) -> None:
    ctx = _fake_ctx({"activate_pending": "true", "activate_stage": activate_stage})
    nudge = "¿Seguimos con su valoración?"

    async def _activate_agent(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield _model_event(nudge, author="activate")

    mock_activate = MagicMock()
    mock_activate.run_async = _activate_agent
    original = root_agent.activate
    root_agent.activate = mock_activate
    try:
        events = [event async for event in root_agent._stream_activate(ctx)]
    finally:
        root_agent.activate = original

    assert len(events) == 1
    assert events[0].author == "be_unique"
    assert events[0].invocation_id == "inv-test"
    assert _event_text(events[0]) == nudge
    assert events[0].actions.state_delta == {
        "activate_pending": "",
        "activate_stage": "",
        "activate_note": "",
    }


@pytest.mark.asyncio
async def test_stream_activate_clears_state_when_nudge_empty() -> None:
    ctx = _fake_ctx({"activate_pending": "true"})

    async def _activate_agent(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        if False:
            yield _model_event("unused")

    mock_activate = MagicMock()
    mock_activate.run_async = _activate_agent
    original = root_agent.activate
    root_agent.activate = mock_activate
    try:
        events = [event async for event in root_agent._stream_activate(ctx)]
    finally:
        root_agent.activate = original

    assert len(events) == 1
    assert events[0].author == "be_unique"
    assert events[0].content is None
    assert events[0].actions.state_delta["activate_pending"] == ""


@pytest.mark.asyncio
async def test_stream_handoff_bridge_copies_invocation_id() -> None:
    ctx = _fake_ctx({})
    spoken = "Le conecto con un asesor."

    async def _bridge_agent(_ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield _model_event(spoken, author="bridge")

    mock_bridge = MagicMock()
    mock_bridge.run_async = _bridge_agent
    original = root_agent.bridge
    root_agent.bridge = mock_bridge
    try:
        events = [
            event
            async for event in root_agent._stream_handoff_bridge(
                ctx,
                fallback_bridge="fallback",
            )
        ]
    finally:
        root_agent.bridge = original

    assert len(events) == 1
    assert events[0].author == "be_unique"
    assert events[0].invocation_id == "inv-test"
    assert _event_text(events[0]) == spoken
