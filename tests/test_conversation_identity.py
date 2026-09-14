from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.deps import AppState


@pytest.mark.asyncio
async def test_uses_conversation_uuid_as_adk_session_id(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.queue.turn import TurnResult

    async def noop(**kwargs):  # type: ignore[no-untyped-def]
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", noop)

    r1 = await client.post("/inbound", json={"waId": "wa-a", "text": "hi"})
    r2 = await client.post("/inbound", json={"waId": "wa-b", "text": "hi"})
    r3 = await client.post("/inbound", json={"waId": "wa-a", "text": "again"})
    assert r1.json()["conversationId"] != r2.json()["conversationId"]
    assert r1.json()["conversationId"] == r3.json()["conversationId"]

    cid = r1.json()["conversationId"]
    closed = await client.post(f"/conversations/{cid}/close")
    assert closed.json()["status"] == "CLOSED"
    r4 = await client.post("/inbound", json={"waId": "wa-a", "text": "new"})
    assert r4.json()["conversationId"] != cid
