from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_stray_click_no_pending_choice_inbox_only(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_text(**kwargs):  # type: ignore[no-untyped-def]
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", no_text)
    # Ensure no ADK session events → real button turn stores choice only
    r = await client.post("/inbound", json={"waId": "stray-1", "text": "hi"})
    cid = r.json()["conversationId"]
    await asyncio.sleep(0.5)
    response = await client.post(
        "/inbound/interactive", json={"conversationId": cid, "buttonId": "x"}
    )
    assert response.status_code == 200
    await asyncio.sleep(0.5)
    messages = await app_state.store.list_messages(cid)
    assert any(m.kind.value == "choice" and m.payload.get("buttonId") == "x" for m in messages)
