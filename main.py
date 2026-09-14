"""ASGI entrypoint for `fastapi dev` / uvicorn compatibility."""

from app.main import app

__all__ = ["app"]
