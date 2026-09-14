from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from app.adapters.whatsapp.handlers import register_handlers
from app.adapters.whatsapp.sink import WhatsAppChannelSink
from app.deps import AppState

logger = logging.getLogger(__name__)


def mount_whatsapp(app: FastAPI, state: AppState) -> Any:
    """Mount PyWa on the FastAPI app when credentials are present."""
    try:
        from pywa_async.client import WhatsApp
    except ImportError:
        from pywa.client import WhatsApp  # type: ignore

    settings = state.settings
    wa = WhatsApp(
        phone_id=settings.whatsapp_phone_number_id,
        token=settings.whatsapp_token,
        server=app,
        webhook_endpoint="/whatsapp/webhook",
        verify_token=settings.whatsapp_verify_token,
        app_secret=settings.whatsapp_app_secret or None,
        validate_updates=bool(settings.whatsapp_app_secret),
        skip_duplicate_updates=True,
    )
    state.channel.add_sink(WhatsAppChannelSink(wa))
    register_handlers(wa, state)
    app.state.whatsapp = wa
    logger.info("WhatsApp (PyWa) mounted at /whatsapp/webhook")
    return wa
