from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_conversation_debug_endpoint(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def noop(**kwargs):  # type: ignore[no-untyped-def]
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", noop)
    r = await client.post("/inbound", json={"waId": "dbg-1", "text": "hi"})
    cid = r.json()["conversationId"]
    import asyncio

    await asyncio.sleep(0.4)
    debug = await client.get(f"/conversations/{cid}/debug")
    assert debug.status_code == 200
    body = debug.json()
    assert body["conversation"]["waId"] == "dbg-1"
    assert isinstance(body["messages"], list)
    assert "sessionEventCount" in body
