from __future__ import annotations

import os

import sentry_sdk
from fastapi import FastAPI

_VERIFY_TRUTHY = frozenset({"1", "true", "yes"})


def _is_dev_mode() -> bool:
    return os.getenv("ADK_DEV_MODE", "").strip().lower() == "true"


def _resolve_release() -> str:
    commit = os.getenv("COMMIT_SHA", "").strip()
    return commit if commit else "dev"


def init_sentry(service_name: str) -> None:
    """Initialize Sentry before the FastAPI app is created. No-op without DSN."""
    dsn = os.getenv("SENTRY_DSN") or None
    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=0,
        environment="development" if _is_dev_mode() else "production",
        release=_resolve_release(),
    )
    sentry_sdk.set_tag("agent", service_name)


def attach_sentry_verify_route(app: FastAPI) -> None:
    """Register GET /sentry-debug only when SENTRY_VERIFY is truthy (not in .env.prod)."""
    flag = os.getenv("SENTRY_VERIFY", "").strip().lower()
    if flag not in _VERIFY_TRUTHY:
        return

    @app.get("/sentry-debug")
    def sentry_debug() -> None:
        raise RuntimeError("Sentry verify")
