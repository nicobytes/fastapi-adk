from __future__ import annotations

import os

"""Environment variable utilities."""


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


"""Asymmetric query string for Gemini Embedding 2 retrieval (pairs with Edge document format)."""


def format_query_for_embedding(user_query: str) -> str:
    """Prefix user text for embed_content — use with the same model as ingest."""
    q = (user_query or "").strip()
    if not q:
        return q
    return f"task: question answering | query: {q}"
