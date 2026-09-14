"""Tenant-agnostic slot availability via Chatty Nest API."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from chatty_agent_common.providers.chatty_api import api_request
from chatty_agent_common.providers.supabase import get_organization_slug
from chatty_agent_common.scheduling._dates import parse_preferred_date

logger = logging.getLogger(__name__)

_DEFAULT_MAX_DAYS = 5
_DEFAULT_MAX_SLOTS_PER_DAY = 6
_PREFERRED_MAX_SLOTS_PER_DAY = 24
_WHATSAPP_MAX_LIST_ROWS = 10

PeriodName = Literal["morning", "afternoon", "evening"]
_VALID_PERIODS: frozenset[str] = frozenset({"morning", "afternoon", "evening"})

_WEEKDAY_ES = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)


def _calendar_day_start_iso(day: str, tz: ZoneInfo) -> str:
    """Nest ``from``: inclusive start of a calendar day in schedule TZ."""
    parsed = date.fromisoformat(day)
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=tz).isoformat()


def _exclusive_end_after_calendar_day(day: str, tz: ZoneInfo) -> str:
    """Nest ``to``: exclusive end = start of the day after ``day`` in schedule TZ."""
    parsed = date.fromisoformat(day)
    next_day = parsed + timedelta(days=1)
    return datetime(next_day.year, next_day.month, next_day.day, tzinfo=tz).isoformat()


def _horizon_end_date(today: date, max_days_ahead: int) -> str:
    """Last bookable calendar day (Nest window end is exclusive at today+N)."""
    return (today + timedelta(days=max_days_ahead - 1)).isoformat()


def _is_beyond_horizon(day: date, today: date, max_days_ahead: int) -> bool:
    first_out = today + timedelta(days=max_days_ahead)
    return day >= first_out


def _hours_available_days_echo(
    day: date,
    *,
    include_day: bool,
) -> list[dict[str, str]]:
    if not include_day:
        return []
    return [{"date": day.isoformat(), "weekday": _weekday_es(day)}]


def _format_time_12h(local: datetime) -> str:
    """Return e.g. ``3:00 PM`` (no leading zero on the hour)."""
    hour24 = local.hour
    minute = local.minute
    suffix = "AM" if hour24 < 12 else "PM"
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12
    return f"{hour12}:{minute:02d} {suffix}"


def _period_of_hour(hour24: int) -> PeriodName:
    if hour24 < 12:
        return "morning"
    if hour24 < 18:
        return "afternoon"
    return "evening"


def _slot_to_agent_view(slot: dict[str, Any], tz: ZoneInfo) -> dict[str, str]:
    start = datetime.fromisoformat(str(slot["start"]).replace("Z", "+00:00"))
    local = start.astimezone(tz)
    time_12h = _format_time_12h(local)
    day = local.date().isoformat()
    return {
        "slot_id": str(slot["id"]),
        "date": day,
        "time": time_12h,
        "period": _period_of_hour(local.hour),
        "label": f"{day} {time_12h}",
    }


def _period_counts(slots: list[dict[str, str]]) -> dict[str, int]:
    counts = {"morning": 0, "afternoon": 0, "evening": 0}
    for slot in slots:
        period = slot.get("period")
        if period in counts:
            counts[period] += 1
    return counts


def _days_from_slots(
    slots: list[dict[str, str]],
    *,
    weekday_by_date: dict[str, str],
) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, str]]] = {}
    for slot in slots:
        by_date.setdefault(slot["date"], []).append(slot)
    days: list[dict[str, Any]] = []
    for date_key in sorted(by_date):
        weekday = weekday_by_date.get(date_key) or _weekday_es(
            date.fromisoformat(date_key)
        )
        days.append({"date": date_key, "weekday": weekday, "slots": by_date[date_key]})
    return days


def _apply_hours_period_policy(
    *,
    slots: list[dict[str, str]],
    days: list[dict[str, Any]],
    available_days: list[dict[str, str]],
    period: str | None,
) -> dict[str, Any]:
    """Filter / gate hours for WhatsApp's 10-row list limit."""
    weekday_by_date = {
        d["date"]: d["weekday"]
        for d in available_days
        if isinstance(d, dict) and d.get("date") and d.get("weekday")
    }
    counts = _period_counts(slots)
    slot_count = len(slots)
    cleaned_period = (period or "").strip().lower() or None

    if cleaned_period is not None and cleaned_period not in _VALID_PERIODS:
        return {
            "status": "error",
            "message": (
                "Invalid period. Use morning, afternoon, or evening (or omit period)."
            ),
            "slots": [],
            "days": [],
            "available_days": available_days,
            "slot_count": 0,
            "period_counts": counts,
            "needs_period_filter": False,
            "truncated": False,
        }

    if cleaned_period is None and slot_count > _WHATSAPP_MAX_LIST_ROWS:
        empty_days = [
            {
                "date": d["date"],
                "weekday": d["weekday"],
                "slots": [],
            }
            for d in available_days
        ]
        return {
            "slots": [],
            "days": empty_days,
            "available_days": available_days,
            "slot_count": slot_count,
            "period_counts": counts,
            "needs_period_filter": True,
            "truncated": False,
            "message": (
                f"{slot_count} horario(s) ese día (más de "
                f"{_WHATSAPP_MAX_LIST_ROWS}). Pregunte franja "
                "(mañana/tarde/noche) según period_counts y re-llame "
                "con period=."
            ),
        }

    filtered = (
        [s for s in slots if s.get("period") == cleaned_period]
        if cleaned_period
        else list(slots)
    )
    filtered_full_count = len(filtered)
    truncated = False
    if filtered_full_count > _WHATSAPP_MAX_LIST_ROWS:
        filtered = filtered[:_WHATSAPP_MAX_LIST_ROWS]
        truncated = True

    out_days = _days_from_slots(filtered, weekday_by_date=weekday_by_date)
    if not out_days and available_days:
        # Keep day metadata even when the chosen period has no slots.
        out_days = [
            {
                "date": d["date"],
                "weekday": d["weekday"],
                "slots": [],
            }
            for d in available_days
        ]

    message_bits: list[str] = []
    if cleaned_period:
        message_bits.append(f"franja {cleaned_period}")
    if truncated:
        message_bits.append(
            f"mostrando {_WHATSAPP_MAX_LIST_ROWS} de {filtered_full_count}; "
            "si prefiere otra hora, que la diga"
        )

    return {
        "slots": filtered,
        "days": out_days if out_days else days,
        "available_days": available_days,
        "slot_count": slot_count,
        "period_counts": counts,
        "needs_period_filter": False,
        "truncated": truncated,
        "message_extra": "; ".join(message_bits) if message_bits else "",
    }


def _weekday_es(day: date) -> str:
    return _WEEKDAY_ES[day.weekday()]


def _parse_day_key(raw: str) -> date | None:
    try:
        return datetime.strptime(raw.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _build_days_payload(
    raw_days: list[dict[str, Any]],
    tz: ZoneInfo,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    """Map Nest grouped days → agent days, flat slots, available_days."""
    days: list[dict[str, Any]] = []
    slots: list[dict[str, str]] = []
    available_days: list[dict[str, str]] = []

    for raw_day in raw_days:
        if not isinstance(raw_day, dict):
            continue
        date_key = str(raw_day.get("date") or "").strip()[:10]
        parsed = _parse_day_key(date_key) if date_key else None
        raw_slots = raw_day.get("slots")
        if not isinstance(raw_slots, list):
            continue

        day_slots: list[dict[str, str]] = []
        for raw_slot in raw_slots:
            if not isinstance(raw_slot, dict):
                continue
            if not raw_slot.get("id") or not raw_slot.get("start"):
                continue
            try:
                view = _slot_to_agent_view(raw_slot, tz)
            except (ValueError, TypeError, KeyError):
                logger.warning(
                    "Skipping malformed slot in grouped days: %s",
                    raw_slot.get("id"),
                )
                continue
            day_slots.append(view)
            slots.append(view)
            if parsed is None:
                parsed = _parse_day_key(view["date"])

        if not day_slots or parsed is None:
            continue

        weekday = _weekday_es(parsed)
        day_date = parsed.isoformat()
        available_days.append({"date": day_date, "weekday": weekday})
        days.append({"date": day_date, "weekday": weekday, "slots": day_slots})

    return days, slots, available_days


def _group_flat_slots(
    raw_slots: list[Any],
    tz: ZoneInfo,
    *,
    max_days: int,
    max_slots_per_day: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    """Legacy flat array → same agent shape (local sample by day)."""
    by_date: dict[str, list[dict[str, str]]] = {}
    for raw_slot in raw_slots:
        if not isinstance(raw_slot, dict):
            continue
        if not raw_slot.get("id") or not raw_slot.get("start"):
            continue
        try:
            view = _slot_to_agent_view(raw_slot, tz)
        except (ValueError, TypeError, KeyError):
            logger.warning(
                "Skipping malformed slot in flat list: %s",
                raw_slot.get("id"),
            )
            continue
        by_date.setdefault(view["date"], []).append(view)

    days: list[dict[str, Any]] = []
    slots: list[dict[str, str]] = []
    available_days: list[dict[str, str]] = []

    for date_key in sorted(by_date)[:max_days]:
        parsed = _parse_day_key(date_key)
        if parsed is None:
            continue
        day_slots = by_date[date_key][:max_slots_per_day]
        weekday = _weekday_es(parsed)
        available_days.append({"date": date_key, "weekday": weekday})
        days.append({"date": date_key, "weekday": weekday, "slots": day_slots})
        slots.extend(day_slots)

    return days, slots, available_days


def run_check_availability(
    *,
    organization_slug: str,
    schedule_slug: str,
    duration_minutes: int | None = None,
    preferred_date: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    timezone: str = "UTC",
    max_days: int = _DEFAULT_MAX_DAYS,
    max_slots_per_day: int | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    """Return open appointment slots for a tenant schedule via Chatty API.

    Discovery (no preferred_date) requests ``groupBy=day`` with up to
    ``max_days`` distinct dates. With preferred_date, returns that day's slots.

    Args:
        organization_slug: ``organizations.slug`` for the tenant (never hardcoded).
        schedule_slug: Platform schedule slug (e.g. location identifier).
        duration_minutes: Optional appointment length override (from RAG);
            when omitted, Nest uses the schedule fallback.
        preferred_date: Optional YYYY-MM-DD (or DD/MM/YYYY / DD-MM-YYYY).
        timezone: IANA timezone for date/time labels and past-date checks.
        max_days: Distinct calendar days for discovery (1-14).
        max_slots_per_day: Cap per day; defaults to 6 (discovery) or 24 (date).
        period: Optional ``morning`` / ``afternoon`` / ``evening`` filter
            (hours mode only). When omitted and a day has more than 10 slots,
            returns ``needs_period_filter`` with empty ``slots``.

    Returns status=ok with ``available_days``, ``days``, and flat ``slots``.
    Each slot includes ``time`` (12h AM/PM) and ``period``.
    """
    cleaned_slug = (organization_slug or "").strip()
    if not cleaned_slug:
        return {
            "status": "error",
            "message": "organization_slug cannot be empty",
            "slots": [],
            "days": [],
            "available_days": [],
        }

    cleaned_schedule = (schedule_slug or "").strip()
    if not cleaned_schedule:
        return {
            "status": "error",
            "message": "schedule_slug cannot be empty",
            "slots": [],
            "days": [],
            "available_days": [],
        }

    preferred = parse_preferred_date(preferred_date)
    parsed_from = parse_preferred_date(from_date)
    parsed_to = parse_preferred_date(to_date)
    if from_date and from_date.strip() and parsed_from is None:
        return {
            "status": "error",
            "error_code": "invalid_date",
            "message": "Unrecognized from_date. Use YYYY-MM-DD.",
            "slots": [],
            "days": [],
            "available_days": [],
        }
    if to_date and to_date.strip() and parsed_to is None:
        return {
            "status": "error",
            "error_code": "invalid_date",
            "message": "Unrecognized to_date. Use YYYY-MM-DD.",
            "slots": [],
            "days": [],
            "available_days": [],
        }
    if preferred_date and preferred_date.strip() and preferred is None:
        return {
            "status": "error",
            "message": (
                "Unrecognized date. Use YYYY-MM-DD (e.g. 2026-08-05) "
                "or leave preferred_date empty."
            ),
            "slots": [],
            "days": [],
            "available_days": [],
        }

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        return {
            "status": "error",
            "message": f"Invalid timezone: {timezone}",
            "slots": [],
            "days": [],
            "available_days": [],
        }

    today = datetime.now(tz).date().isoformat()
    if preferred is not None and preferred < today:
        return {
            "status": "error",
            "message": (
                f"Date {preferred} is in the past (today is {today} in "
                f"{timezone}). Ask for a future date."
            ),
            "slots": [],
            "days": [],
            "available_days": [],
        }

    bounded_days = max(1, min(int(max_days), 14))
    per_day = (
        max_slots_per_day
        if max_slots_per_day is not None
        else (_PREFERRED_MAX_SLOTS_PER_DAY if preferred else _DEFAULT_MAX_SLOTS_PER_DAY)
    )
    bounded_per_day = max(1, min(int(per_day), 48))

    try:
        org_id = get_organization_slug(cleaned_slug)
        query: dict[str, str] = {
            "organizationId": org_id,
            "scheduleSlug": cleaned_schedule,
            "groupBy": "day",
            "maxSlotsPerDay": str(bounded_per_day),
        }
        if duration_minutes is not None:
            query["durationMinutes"] = str(int(duration_minutes))
        if preferred:
            query["preferredDate"] = preferred
        else:
            query["maxDays"] = str(bounded_days)
            if parsed_from:
                query["from"] = _calendar_day_start_iso(parsed_from, tz)
            if parsed_to:
                query["to"] = _exclusive_end_after_calendar_day(parsed_to, tz)
        raw = api_request("GET", "/scheduling/slots", query=query)
    except (RuntimeError, ValueError) as exc:
        logger.exception("run_check_availability failed")
        return {
            "status": "error",
            "message": str(exc),
            "slots": [],
            "days": [],
            "available_days": [],
        }

    if isinstance(raw, dict) and isinstance(raw.get("days"), list):
        days, slots, available_days = _build_days_payload(raw["days"], tz)
    elif isinstance(raw, list):
        days, slots, available_days = _group_flat_slots(
            raw,
            tz,
            max_days=1 if preferred else bounded_days,
            max_slots_per_day=bounded_per_day,
        )
    else:
        return {
            "status": "error",
            "message": "Invalid response from scheduling API.",
            "slots": [],
            "days": [],
            "available_days": [],
        }

    if not slots:
        return {
            "status": "ok",
            "schedule_slug": cleaned_schedule,
            "duration_minutes": duration_minutes,
            "slots": [],
            "days": [],
            "available_days": [],
            "slot_count": 0,
            "period_counts": {"morning": 0, "afternoon": 0, "evening": 0},
            "needs_period_filter": False,
            "truncated": False,
            "message": "No open slots in the requested window. Try another date.",
        }

    if preferred:
        policy = _apply_hours_period_policy(
            slots=slots,
            days=days,
            available_days=available_days,
            period=period,
        )
        if policy.get("status") == "error":
            return {
                **policy,
                "schedule_slug": cleaned_schedule,
                "duration_minutes": duration_minutes,
            }
        first = available_days[0]
        base_msg = (
            f"Cupos para {first['weekday']} {first['date']}: "
            f"{policy['slot_count']} horario(s)."
        )
        if policy.get("message"):
            message = str(policy["message"])
        elif policy.get("message_extra"):
            message = f"{base_msg} ({policy['message_extra']})."
        else:
            message = base_msg
        return {
            "status": "ok",
            "schedule_slug": cleaned_schedule,
            "duration_minutes": duration_minutes,
            "slots": policy["slots"],
            "days": policy["days"],
            "available_days": policy["available_days"],
            "slot_count": policy["slot_count"],
            "period_counts": policy["period_counts"],
            "needs_period_filter": policy["needs_period_filter"],
            "truncated": policy["truncated"],
            "message": message,
        }

    day_labels = ", ".join(d["weekday"] for d in available_days)
    payload: dict[str, Any] = {
        "status": "ok",
        "schedule_slug": cleaned_schedule,
        "duration_minutes": duration_minutes,
        "slots": slots,
        "days": days,
        "available_days": available_days,
        "message": f"{len(available_days)} día(s) con cupos: {day_labels}.",
    }
    if parsed_from:
        payload["from_date"] = parsed_from
    if parsed_to:
        payload["to_date"] = parsed_to
    return payload


def run_list_available_days(
    *,
    organization_slug: str,
    schedule_slug: str,
    duration_minutes: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    timezone: str = "UTC",
    max_days: int = _DEFAULT_MAX_DAYS,
) -> dict[str, Any]:
    """Discovery mode: return available calendar days without times.

    Optional ``from_date`` / ``to_date`` anchor discovery (inclusive calendar
    days; Nest ``to`` is exclusive at start of day after ``to_date``).
    Strips ``slots`` / ``days`` so agents cannot offer HH:MM in phase 1.
    """
    result = run_check_availability(
        organization_slug=organization_slug,
        schedule_slug=schedule_slug,
        duration_minutes=duration_minutes,
        preferred_date=None,
        from_date=from_date,
        to_date=to_date,
        timezone=timezone,
        max_days=max_days,
    )
    available_days = [
        {"date": d["date"], "weekday": d["weekday"]}
        for d in result.get("available_days", [])
        if isinstance(d, dict) and d.get("date") and d.get("weekday")
    ]
    return {
        "status": result.get("status", "error"),
        "schedule_slug": result.get("schedule_slug", schedule_slug),
        "duration_minutes": result.get("duration_minutes", duration_minutes),
        "available_days": available_days,
        "from_date": result.get("from_date"),
        "to_date": result.get("to_date"),
        "days": [],
        "slots": [],
        "message": str(
            result.get("message")
            or (
                f"{len(available_days)} día(s) con cupos."
                if available_days
                else "No open slots in the requested window. Try another date."
            )
        ),
    }


def run_list_available_hours(
    *,
    organization_slug: str,
    schedule_slug: str,
    date: str,
    duration_minutes: int | None = None,
    timezone: str = "UTC",
    period: str | None = None,
    max_days_ahead: int | None = None,
) -> dict[str, Any]:
    """Hours mode: return slots for one calendar day (``date`` required).

    ``date`` may be any future ISO day the client named — it does **not** have
    to appear in a prior ``available_days`` discovery list. Optional
    ``max_days_ahead`` (from schedule catalog) enables local ``beyond_horizon``
    classification without a Nest GET.
    """
    cleaned = (date or "").strip()
    if not cleaned:
        return {
            "status": "error",
            "error_code": "invalid_date",
            "message": (
                "date is required (YYYY-MM-DD). Call after the client "
                "named or picked a calendar day."
            ),
            "slots": [],
            "days": [],
            "available_days": [],
        }
    parsed_iso = parse_preferred_date(cleaned)
    if parsed_iso is None:
        return {
            "status": "error",
            "error_code": "invalid_date",
            "message": ("Unrecognized date. Use YYYY-MM-DD (e.g. 2026-08-05)."),
            "slots": [],
            "days": [],
            "available_days": [],
        }

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        return {
            "status": "error",
            "error_code": "api_failure",
            "message": f"Invalid timezone: {timezone}",
            "date": parsed_iso,
            "slots": [],
            "days": [],
            "available_days": [],
        }

    today = datetime.now(tz).date()
    parsed_day = datetime.fromisoformat(parsed_iso).date()
    horizon_end: str | None = None
    if max_days_ahead is not None and max_days_ahead > 0:
        horizon_end = _horizon_end_date(today, max_days_ahead)

    if parsed_day < today:
        return {
            "status": "error",
            "error_code": "past",
            "date": parsed_iso,
            "message": (
                f"Date {parsed_iso} is in the past (today is {today.isoformat()} in "
                f"{timezone}). Ask for a future date."
            ),
            "slots": [],
            "days": [],
            "available_days": [],
            "horizon_end": horizon_end,
        }

    if (
        max_days_ahead is not None
        and max_days_ahead > 0
        and _is_beyond_horizon(parsed_day, today, max_days_ahead)
    ):
        return {
            "status": "ok",
            "date": parsed_iso,
            "availability_kind": "beyond_horizon",
            "horizon_end": horizon_end,
            "slots": [],
            "days": [],
            "available_days": [],
            "slot_count": 0,
            "period_counts": {"morning": 0, "afternoon": 0, "evening": 0},
            "needs_period_filter": False,
            "truncated": False,
            "message": "No open slots in the requested window. Try another date.",
        }

    result = run_check_availability(
        organization_slug=organization_slug,
        schedule_slug=schedule_slug,
        duration_minutes=duration_minutes,
        preferred_date=parsed_iso,
        timezone=timezone,
        period=period,
    )

    base = {
        "date": parsed_iso,
        "horizon_end": horizon_end,
    }

    if result.get("status") == "error":
        msg = str(result.get("message") or "")
        code = "invalid_period" if "invalid period" in msg.casefold() else "api_failure"
        err: dict[str, Any] = {
            **base,
            "status": "error",
            "error_code": code,
            "message": msg or "Error consulting availability.",
            "slots": [],
            "days": [],
            "available_days": [],
        }
        return err

    slots = result.get("slots") or []
    needs_period_filter = bool(result.get("needs_period_filter"))
    day_echo = _hours_available_days_echo(
        parsed_day, include_day=bool(slots or needs_period_filter)
    )

    if slots or needs_period_filter:
        return {
            **base,
            "status": "ok",
            "availability_kind": "has_slots",
            "schedule_slug": result.get("schedule_slug", schedule_slug),
            "duration_minutes": result.get("duration_minutes", duration_minutes),
            "slots": slots,
            "days": result.get("days") or [],
            "available_days": day_echo,
            "slot_count": result.get("slot_count", len(slots)),
            "period_counts": result.get(
                "period_counts",
                {"morning": 0, "afternoon": 0, "evening": 0},
            ),
            "needs_period_filter": needs_period_filter,
            "truncated": bool(result.get("truncated")),
            "message": str(
                result.get("message") or f"{len(slots)} horario(s) disponibles."
            ),
        }

    return {
        **base,
        "status": "ok",
        "availability_kind": "empty_day",
        "schedule_slug": result.get("schedule_slug", schedule_slug),
        "duration_minutes": result.get("duration_minutes", duration_minutes),
        "slots": [],
        "days": [],
        "available_days": [],
        "slot_count": 0,
        "period_counts": {"morning": 0, "afternoon": 0, "evening": 0},
        "needs_period_filter": False,
        "truncated": False,
        "message": "No open slots in the requested window. Try another date.",
    }
