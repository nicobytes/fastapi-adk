from __future__ import annotations

import asyncio
import time

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_returns_http_before_the_runner_finishes(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = asyncio.Event()
    finished = asyncio.Event()

    async def slow_turn(**kwargs):  # type: ignore[no-untyped-def]
        started.set()
        await asyncio.sleep(1.5)
        finished.set()
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", slow_turn)

    t0 = time.perf_counter()
    response = await client.post(
        "/inbound", json={"waId": "5215511111111", "text": "hola"}
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["conversationId"]
    assert body["status"] == "BOT_AUTO"
    assert elapsed_ms < 100

    await asyncio.wait_for(started.wait(), timeout=2)
    assert not finished.is_set()
    await asyncio.wait_for(finished.wait(), timeout=3)
