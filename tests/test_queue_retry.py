from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_retries_a_failed_job_and_then_runs_the_agent(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"n": 0}
    done = asyncio.Event()

    async def flaky_turn(**kwargs):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        done.set()
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", flaky_turn)

    response = await client.post(
        "/inbound", json={"waId": "5215522222222", "text": "retry me"}
    )
    assert response.status_code == 200
    await asyncio.wait_for(done.wait(), timeout=5)
    assert calls["n"] >= 2
