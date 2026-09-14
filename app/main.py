from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.deps import build_app_state, shutdown_app_state
from app.http import conversations, health, inbound, operator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    state = await build_app_state(settings)
    app.state.app_state = state
    if settings.whatsapp_configured:
        from app.adapters.whatsapp.client import mount_whatsapp

        mount_whatsapp(app, state)
    yield
    await shutdown_app_state(state)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="fastapi-adk", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(health.router)
    app.include_router(inbound.router)
    app.include_router(operator.router)
    app.include_router(conversations.router)
    return app


app = create_app()
