from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.deps import build_app_state, shutdown_app_state
from app.http import inbound
from app.queue.turn import TurnResult


@pytest.mark.asyncio
async def test_runs_a_delayed_job_after_process_restart(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_name = f"fastapi-adk-restart-{tmp_path.name}"
    base = dict(
        redis_url="redis://127.0.0.1:6379",
        session_db_url=f"sqlite+aiosqlite:///{tmp_path / 'sessions.sqlite'}",
        poc_db_url=f"sqlite+aiosqlite:///{tmp_path / 'poc.sqlite'}",
        queue_name=queue_name,
        buffer_ms=1.5,
        google_api_key="",
    )

    # Process 1: accept + enqueue, no worker
    settings1 = Settings(**base, embed_worker=False)
    state1 = await build_app_state(settings1)
    app = FastAPI()
    app.state.app_state = state1
    app.include_router(inbound.router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/inbound", json={"waId": "5215533333333", "text": "survive"}
        )
        assert response.status_code == 200
    await shutdown_app_state(state1)

    # Process 2: new worker picks up delayed job
    ran = asyncio.Event()

    async def mark_ran(**kwargs):  # type: ignore[no-untyped-def]
        ran.set()
        return TurnResult()

    settings2 = Settings(**base, embed_worker=True)
    state2 = await build_app_state(settings2)
    monkeypatch.setattr(state2.turn_service, "run_text_turn", mark_ran)
    try:
        await asyncio.wait_for(ran.wait(), timeout=5)
    finally:
        await shutdown_app_state(state2)
