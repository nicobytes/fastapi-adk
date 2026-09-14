from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.deps import AppState
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_batches_three_inbound_texts_into_one_run_async(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []
    done = asyncio.Event()

    async def capture(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(kwargs["text"])
        done.set()
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", capture)
    app_state.settings.buffer_ms = 0.4

    for text in ("a", "b", "c"):
        response = await client.post(
            "/inbound", json={"waId": "5215544444444", "text": text}
        )
        assert response.status_code == 200
        await asyncio.sleep(0.05)

    await asyncio.wait_for(done.wait(), timeout=3)
    assert len(seen) == 1
    assert seen[0] == "a\nb\nc"


@pytest.mark.asyncio
async def test_follow_up_job_drains_texts_that_arrived_while_busy(
    client: AsyncClient, app_state: AppState, monkeypatch: pytest.MonkeyPatch
) -> None:
    texts: list[str] = []
    first_started = asyncio.Event()
    second_done = asyncio.Event()

    async def gated(**kwargs):  # type: ignore[no-untyped-def]
        texts.append(kwargs["text"])
        if len(texts) == 1:
            first_started.set()
            await asyncio.sleep(0.8)
        else:
            second_done.set()
        return TurnResult()

    monkeypatch.setattr(app_state.turn_service, "run_text_turn", gated)
    app_state.settings.buffer_ms = 0.2

    r1 = await client.post("/inbound", json={"waId": "5215555555555", "text": "first"})
    assert r1.status_code == 200
    await asyncio.wait_for(first_started.wait(), timeout=2)
    r2 = await client.post("/inbound", json={"waId": "5215555555555", "text": "during"})
    assert r2.status_code == 200
    await asyncio.wait_for(second_done.wait(), timeout=3)
    assert any("during" in item for item in texts)
