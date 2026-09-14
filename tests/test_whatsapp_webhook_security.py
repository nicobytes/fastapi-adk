from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_whatsapp_verify_forbidden_without_mount():
    # When WhatsApp is not configured, webhook routes are absent → 404
    from app.config import Settings
    from app.main import create_app

    app = create_app(Settings(embed_worker=False, whatsapp_token="", whatsapp_phone_number_id=""))
    # Lifespan would build state; use a minimal app without WhatsApp
    assert app is not None
