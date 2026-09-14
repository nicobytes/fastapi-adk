"""VertexAiSessionService must use ADC, not a leftover GOOGLE_API_KEY."""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from app.app_utils.services import get_session_service


@pytest.fixture(autouse=True)
def _clear_session_service_cache() -> Generator[None, None, None]:
    get_session_service.cache_clear()
    yield
    get_session_service.cache_clear()


def test_vertex_session_service_strips_api_key_and_keeps_runtime_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SESSION_SERVICE_URI", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_AGENT_ENGINE_ID", "engine-1")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "chatty-agents-ia")
    monkeypatch.setenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION", "us-central1")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    monkeypatch.setenv("GOOGLE_API_KEY", "studio-key")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "1")

    captured: dict[str, Any] = {}

    class FakeVertexAiSessionService:
        def __init__(self, **kwargs: Any) -> None:
            captured["kwargs"] = kwargs
            captured["api_key_during_init"] = os.environ.get("GOOGLE_API_KEY")

    with patch(
        "google.adk.sessions.vertex_ai_session_service.VertexAiSessionService",
        FakeVertexAiSessionService,
    ):
        service = get_session_service()

    assert isinstance(service, FakeVertexAiSessionService)
    assert captured["api_key_during_init"] is None
    assert os.environ.get("GOOGLE_API_KEY") is None
    assert captured["kwargs"]["project"] == "chatty-agents-ia"
    assert captured["kwargs"]["location"] == "us-central1"
    assert captured["kwargs"]["agent_engine_id"] == "engine-1"
    assert os.environ.get("GOOGLE_CLOUD_LOCATION") == "global"


def test_in_memory_when_not_on_agent_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SESSION_SERVICE_URI", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_AGENT_ENGINE_ID", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "studio-key")

    service = get_session_service()
    assert isinstance(service, InMemorySessionService)
    assert os.environ.get("GOOGLE_API_KEY") == "studio-key"
