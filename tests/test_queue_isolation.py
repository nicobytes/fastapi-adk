from __future__ import annotations

import asyncio
import time

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_serves_another_conversation_while_run_async_in_flight(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = asyncio.Event()

    async def slow(**kwargs):  # type: ignore[no-untyped-def]
        started.set()
        await asyncio.sleep(1.5)
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", slow)

    r1 = await client.post("/inbound", json={"waId": "5215566666666", "text": "slow"})
    assert r1.status_code == 200
    await asyncio.wait_for(started.wait(), timeout=2)

    t0 = time.perf_counter()
    health = await client.get("/health")
    r2 = await client.post("/inbound", json={"waId": "5215577777777", "text": "other"})
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert health.status_code == 200
    assert health.json()["ok"] is True
    assert r2.status_code == 200
    assert elapsed_ms < 200
    # Allow slow turn to finish so fixture teardown is clean
    await asyncio.sleep(1.6)
