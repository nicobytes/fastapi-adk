"""Supabase catalog for schedules (service role)."""

from __future__ import annotations

from typing import Any, TypedDict

import httpx

from chatty_agent_common.providers.supabase import get_supabase_client

_CONNECT_ERROR_HINT = (
    "Cannot connect to Supabase (check SUPABASE_URL). If you run the agent on your "
    "machine, use the local API URL from `supabase status` (typically "
    "http://127.0.0.1:54321)."
)

__all__ = [
    "ScheduleRow",
    "list_schedules",
    "resolve_schedule",
]


class ScheduleRow(TypedDict):
    id: str
    name: str
    slug: str
    timezone: str
    duration_minutes: int
    is_default: bool
    is_active: bool
    max_days_ahead: int | None


_SCHEDULE_COLUMNS = (
    "id, name, slug, timezone, duration_minutes, is_default, is_active, max_days_ahead"
)


def list_schedules(organization_id: str) -> list[ScheduleRow]:
    """Active schedules for an organization (service role; bypasses RLS)."""
    org_id = (organization_id or "").strip()
    if not org_id:
        raise ValueError("organization_id cannot be empty")

    client = get_supabase_client()
    try:
        response = (
            client.table("schedules")
            .select(_SCHEDULE_COLUMNS)
            .eq("organization_id", org_id)
            .eq("is_active", True)
            .order("is_default", desc=True)
            .order("name")
            .execute()
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc

    return [_map_schedule(row) for row in _rows(response.data, "schedules")]


def _normalize_sede_needle(sede: str) -> str:
    """Normalize sede text for matching (strip ``sede_`` button-id prefix)."""
    cleaned = (sede or "").strip()
    if cleaned.casefold().startswith("sede_"):
        return cleaned[5:].strip()
    return cleaned


def resolve_schedule(
    schedules: list[ScheduleRow],
    sede: str,
) -> tuple[ScheduleRow | None, str | None]:
    """Match ``sede`` to a schedule by name or slug (case-insensitive).

    - Zero schedules → error.
    - One schedule → return it always (single-schedule tenant).
    - Multiple → exact name/slug match (also accepts ``sede_<slug>``).
      No silent fallback to ``is_default``.
    """
    if not schedules:
        return None, "No hay horarios activos configurados."

    if len(schedules) == 1:
        return schedules[0], None

    cleaned = _normalize_sede_needle(sede)
    if not cleaned:
        return None, "Falta la sede o horario."

    needle = cleaned.casefold()
    for schedule in schedules:
        if (
            schedule["name"].casefold() == needle
            or schedule["slug"].casefold() == needle
        ):
            return schedule, None

    available = ", ".join(schedule["name"] for schedule in schedules)
    return None, f"Sede inválida. Opciones: {available}."


def _rows(data: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        raise RuntimeError(f"{label} query returned an invalid payload")
    rows: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            raise RuntimeError(f"{label} query returned an invalid row shape")
        rows.append(row)
    return rows


def _map_schedule(row: dict[str, Any]) -> ScheduleRow:
    schedule_id = row.get("id")
    name = row.get("name")
    slug = row.get("slug")
    timezone = row.get("timezone")
    if not isinstance(schedule_id, str) or not schedule_id:
        raise RuntimeError("Schedule row missing id")
    if not isinstance(name, str) or not name:
        raise RuntimeError("Schedule row missing name")
    if not isinstance(slug, str) or not slug:
        raise RuntimeError("Schedule row missing slug")
    if not isinstance(timezone, str) or not timezone:
        raise RuntimeError("Schedule row missing timezone")
    duration = row.get("duration_minutes")
    if not isinstance(duration, int) or duration <= 0:
        duration = 60
    raw_horizon = row.get("max_days_ahead")
    max_days_ahead: int | None
    if isinstance(raw_horizon, int) and raw_horizon > 0:
        max_days_ahead = raw_horizon
    else:
        max_days_ahead = None
    return {
        "id": schedule_id,
        "name": name,
        "slug": slug,
        "timezone": timezone,
        "duration_minutes": duration,
        "is_default": bool(row.get("is_default")),
        "is_active": bool(row.get("is_active", True)),
        "max_days_ahead": max_days_ahead,
    }
