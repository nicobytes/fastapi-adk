from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.config import Settings
from app.deps import build_app_state, shutdown_app_state
from app.adapters.whatsapp.handlers import register_handlers


class _FakeMsg:
    def __init__(self, mid: str, wa_id: str, text: str) -> None:
        self.id = mid
        self.text = text
        self.from_user = type("U", (), {"wa_id": wa_id})()


class _FakeWa:
    def __init__(self) -> None:
        self._message_handlers = []
        self._button_handlers = []

    def on_message(self):
        def deco(fn):
            self._message_handlers.append(fn)
            return fn

        return deco

    def on_callback_button(self):
        def deco(fn):
            self._button_handlers.append(fn)
            return fn

        return deco


@pytest.mark.asyncio
async def test_whatsapp_dedupe(tmp_path) -> None:
    settings = Settings(
        redis_url="redis://127.0.0.1:6379",
        session_db_url=f"sqlite+aiosqlite:///{tmp_path / 'sessions.sqlite'}",
        poc_db_url=f"sqlite+aiosqlite:///{tmp_path / 'poc.sqlite'}",
        queue_name=f"wa-dedupe-{tmp_path.name}",
        embed_worker=False,
        buffer_ms=0.2,
    )
    state = await build_app_state(settings)
    wa = _FakeWa()
    register_handlers(wa, state)
    try:
        msg = _FakeMsg("m1", "5215588888888", "hola")
        await wa._message_handlers[0](wa, msg)
        await wa._message_handlers[0](wa, msg)
        messages = await state.store.list_messages(
            (await state.store.find_or_create_open("5215588888888")).id
        )
        # find_or_create may create second if first closed — count customer texts with hola
        # After first handler, one conversation; second ignored by dedupe
        conv = await state.store.find_or_create_open("5215588888888")
        messages = await state.store.list_messages(conv.id)
        assert sum(1 for m in messages if m.body == "hola") == 1
    finally:
        await shutdown_app_state(state)
