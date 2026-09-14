from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.conversation_lock import ConversationLock
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_click_waits_for_active_text_turn(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    order: list[str] = []
    text_started = asyncio.Event()
    button_done = asyncio.Event()

    async def slow_text(**kwargs):  # type: ignore[no-untyped-def]
        order.append("text_start")
        text_started.set()
        await asyncio.sleep(0.6)
        order.append("text_end")
        return TurnResult()

    async def button(**kwargs):  # type: ignore[no-untyped-def]
        order.append("button")
        button_done.set()
        return TurnResult(skipped=True, reason="no_pending_choice", stored=True)

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", slow_text)
    monkeypatch.setattr(app_state.turn_service, "run_button_turn", button)
    app_state.settings.buffer_ms = 0.15

    r = await client.post("/inbound", json={"waId": "ser-1", "text": "hello"})
    cid = r.json()["conversationId"]
    await asyncio.wait_for(text_started.wait(), timeout=2)
    await client.post(
        "/inbound/interactive", json={"conversationId": cid, "buttonId": "b"}
    )
    await asyncio.wait_for(button_done.wait(), timeout=3)
    assert order.index("text_end") < order.index("button")
