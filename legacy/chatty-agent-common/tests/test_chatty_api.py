"""Unit tests for Nest Chatty API HTTP client."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from chatty_agent_common.providers.chatty_api import api_request


@pytest.fixture(autouse=True)
def _api_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHATTY_API_URL", "http://api.test")
    monkeypatch.setenv("API_WEBHOOK_SECRET", "test-secret")


def test_missing_config_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHATTY_API_URL", raising=False)
    monkeypatch.delenv("API_WEBHOOK_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="CHATTY_API_URL"):
        api_request("GET", "/scheduling/slots")


def test_get_with_query_parses_json() -> None:
    response = MagicMock()
    response.read.return_value = b'[{"id":"s1"}]'
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)

    with patch(
        "chatty_agent_common.providers.chatty_api.urllib.request.urlopen",
        return_value=response,
    ) as urlopen:
        result = api_request(
            "GET",
            "/scheduling/slots",
            query={"organizationId": "org-1"},
        )

    assert result == [{"id": "s1"}]
    request = urlopen.call_args.args[0]
    assert "organizationId=org-1" in request.full_url
    assert request.get_header("Authorization") == "Bearer test-secret"


def test_http_error_raises_runtime() -> None:
    err = HTTPError(
        "http://api.test/x",
        400,
        "Bad Request",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(json.dumps({"message": "bad input"}).encode()),
    )
    with patch(
        "chatty_agent_common.providers.chatty_api.urllib.request.urlopen",
        side_effect=err,
    ):
        with pytest.raises(RuntimeError, match="API 400: bad input"):
            api_request("GET", "/x")


def test_url_error_raises_runtime() -> None:
    with patch(
        "chatty_agent_common.providers.chatty_api.urllib.request.urlopen",
        side_effect=URLError("refused"),
    ):
        with pytest.raises(RuntimeError, match="Could not reach Chatty API"):
            api_request("GET", "/x")
