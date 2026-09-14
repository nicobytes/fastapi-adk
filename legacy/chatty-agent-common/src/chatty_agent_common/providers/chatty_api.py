"""HTTP client for NestJS Chatty API (webhook Bearer auth)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def api_base() -> str:
    return (os.environ.get("CHATTY_API_URL") or "").rstrip("/")


def api_secret() -> str:
    """Same value as Nest ``API_WEBHOOK_SECRET`` / Supabase vault ``api_webhook_secret``."""
    return (os.environ.get("API_WEBHOOK_SECRET") or "").strip()


def api_request(
    method: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 20,
) -> dict[str, Any] | list[Any]:
    """Call Chatty Nest API with Bearer webhook secret.

    Raises:
        RuntimeError: Missing config, HTTP error, or network failure.
    """
    base = api_base()
    secret = api_secret()
    if not base or not secret:
        raise RuntimeError("CHATTY_API_URL and API_WEBHOOK_SECRET must be configured.")

    url = f"{base}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(err_body)
            message = payload.get("message") or err_body
        except json.JSONDecodeError:
            message = err_body or str(exc)
        if isinstance(message, list):
            message = "; ".join(str(m) for m in message)
        raise RuntimeError(f"API {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Chatty API: {exc.reason}") from exc
