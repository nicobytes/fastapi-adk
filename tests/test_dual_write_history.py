from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_inbox_and_adk_session_are_dual_write_not_prompt_injection(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_turn(**kwargs):  # type: ignore[no-untyped-def]
        cid = kwargs["conversation_id"]
        app_state.channel.bind(cid, "fake", "wa")
        await app_state.channel.send_text(cid, "bot says hi")
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", fake_turn)
    app_state.settings.buffer_ms = 0.2
    r = await client.post("/inbound", json={"waId": "dual-1", "text": "customer hi"})
    cid = r.json()["conversationId"]
    await asyncio.sleep(0.6)
    messages = await app_state.store.list_messages(cid)
    roles = {(m.role.value, m.kind.value) for m in messages}
    assert ("customer", "text") in roles
    assert ("bot", "text") in roles
