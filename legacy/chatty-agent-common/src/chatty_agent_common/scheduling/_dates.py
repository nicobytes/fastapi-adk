"""Date parsing helpers for scheduling tools."""

from __future__ import annotations

from datetime import datetime


def parse_preferred_date(preferred_date: str | None) -> str | None:
    """Parse YYYY-MM-DD / DD/MM/YYYY / DD-MM-YYYY to ISO date, or None if empty."""
    if not preferred_date or not preferred_date.strip():
        return None
    raw = preferred_date.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None
