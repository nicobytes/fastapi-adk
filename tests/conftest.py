from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.deps import AppState, build_app_state, shutdown_app_state
from app.http import conversations, health, inbound, operator
from fastapi import FastAPI


@pytest.fixture
async def app_state(tmp_path: Path) -> AsyncIterator[AppState]:
    settings = Settings(
        redis_url="redis://127.0.0.1:6379",
        session_db_url=f"sqlite+aiosqlite:///{tmp_path / 'sessions.sqlite'}",
        poc_db_url=f"sqlite+aiosqlite:///{tmp_path / 'poc.sqlite'}",
        queue_name=f"fastapi-adk-test-{tmp_path.name}",
        buffer_ms=0.4,
        embed_worker=True,
        google_api_key="",
    )
    state = await build_app_state(settings)
    await asyncio.sleep(0.3)
    try:
        yield state
    finally:
        await shutdown_app_state(state)


@pytest.fixture
async def client(app_state: AppState) -> AsyncIterator[AsyncClient]:
    app = FastAPI()
    app.state.settings = app_state.settings
    app.state.app_state = app_state
    app.include_router(health.router)
    app.include_router(inbound.router)
    app.include_router(operator.router)
    app.include_router(conversations.router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
