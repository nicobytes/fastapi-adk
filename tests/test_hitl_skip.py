from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.conversations.types import ConversationStatus
from app.deps import AppState
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_skips_the_runner_when_conversation_is_waiting_human(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"n": 0}

    async def count(**kwargs):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", count)
    app_state.settings.buffer_ms = 0.2

    r = await client.post("/inbound", json={"waId": "hitl-1", "text": "hello"})
    cid = r.json()["conversationId"]
    await asyncio.sleep(0.5)
    assert calls["n"] == 1

    await client.post(f"/conversations/{cid}/handoff")
    await client.post("/inbound", json={"waId": "hitl-1", "text": "after handoff"})
    await asyncio.sleep(0.5)
    assert calls["n"] == 1
    messages = await app_state.store.list_messages(cid)
    assert any(m.body == "after handoff" for m in messages)

    await client.post(f"/conversations/{cid}/release")
    await client.post("/inbound", json={"waId": "hitl-1", "text": "back"})
    await asyncio.sleep(0.5)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_already_scheduled_job_still_runs_after_handoff(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran = asyncio.Event()

    async def mark(**kwargs):  # type: ignore[no-untyped-def]
        ran.set()
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", mark)
    app_state.settings.buffer_ms = 0.8

    r = await client.post("/inbound", json={"waId": "hitl-2", "text": "scheduled"})
    cid = r.json()["conversationId"]
    await client.post(f"/conversations/{cid}/handoff")
    await asyncio.wait_for(ran.wait(), timeout=3)
