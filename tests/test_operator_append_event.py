from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.turn import TurnResult
from tests.has_key import has_gemini_key


@pytest.mark.asyncio
@pytest.mark.skipif(not has_gemini_key(), reason="GOOGLE_API_KEY not set")
async def test_operator_reply_is_visible_to_the_next_agent_turn(
    client: AsyncClient, app_state: AppState
) -> None:
    # Live path: operator fact then customer question — requires Gemini
    r = await client.post("/inbound", json={"waId": "op-1", "text": "hola"})
    cid = r.json()["conversationId"]
    import asyncio

    await asyncio.sleep(3)
    await client.post(
        "/operator/reply", json={"conversationId": cid, "text": "el precio es 100"}
    )
    await client.post("/inbound", json={"waId": "op-1", "text": "cual es el precio?"})
    await asyncio.sleep(5)
    outbound = [m for m in app_state.channel.list(cid) if m.kind == "text"]
    assert any("100" in str(m.payload.get("text", "")) for m in outbound)
