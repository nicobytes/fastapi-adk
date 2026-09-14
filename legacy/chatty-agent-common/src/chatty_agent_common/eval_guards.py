"""Deterministic eval guards for user-visible agent output."""

from __future__ import annotations

__all__ = [
    "FORBIDDEN_USER_FACING_LEAKS",
    "find_forbidden_leaks",
]

# Substrings that must never appear in WhatsApp-facing model text.
FORBIDDEN_USER_FACING_LEAKS: tuple[str, ...] = (
    "handoff",
    "estado interno",
    "esperaré",
    "esperara",
    "bant",
    "intervención conversacional",
    "intervencion conversacional",
    "próxima intervención",
    "proxima intervencion",
    "puramente informativo",
    "[chatty_activate]",
)


def find_forbidden_leaks(text: str) -> list[str]:
    """Return forbidden leak phrases found in ``text`` (case-insensitive)."""
    lowered = text.lower()
    return [phrase for phrase in FORBIDDEN_USER_FACING_LEAKS if phrase in lowered]
