"""List, cancel, and reschedule bookings via Supabase (service role)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from postgrest.exceptions import APIError

from chatty_agent_common.providers.chatty_api import api_request
from chatty_agent_common.providers.supabase import get_organization_slug
from chatty_agent_common.scheduling.catalog import ScheduleRow, list_schedules

logger = logging.getLogger(__name__)

_SLOT_ID_SEPARATOR = "|"
_EXCLUSION_VIOLATION = "23P01"
_BOOKING_SELECT = (
    "id, service_name, start_at, end_at, status, schedule_id, "
    "conversation_id, customer_id, "
    "schedules(name, slug, timezone, duration_minutes)"
)

_WEEKDAY_ES = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)

_CONNECT_ERROR_HINT = (
    "Cannot connect to Supabase (check SUPABASE_URL). If you run the agent on your "
    "machine, use the local API URL from `supabase status` (typically "
    "http://127.0.0.1:54321)."
)

__all__ = [
    "parse_slot_id",
    "run_cancel_appointment",
    "run_list_conversation_bookings",
    "run_reschedule_appointment",
]


def parse_slot_id(slot_id: str) -> tuple[str, datetime] | None:
    """Parse ``scheduleSlug|ISO-start`` (same format as Nest ``parseSlotId``)."""
    cleaned = (slot_id or "").strip()
    separator_index = cleaned.rfind(_SLOT_ID_SEPARATOR)
    if separator_index <= 0:
        return None

    schedule_slug = cleaned[:separator_index]
    start_raw = cleaned[separator_index + 1 :]
    if not schedule_slug.strip():
        return None

    try:
        start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return schedule_slug, start


def run_list_conversation_bookings(
    *,
    organization_slug: str,
    conversation_id: str | None,
    timezone: str = "America/La_Paz",
) -> dict[str, Any]:
    """Return confirmed vigentes for this conversation's contact."""
    org_err = _validate_org_slug(organization_slug)
    if org_err:
        return org_err

    conv_id = _clean_conversation_id(conversation_id)
    if not conv_id:
        return _no_conversation_error()

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        return {"status": "error", "message": f"Invalid timezone: {timezone}"}

    try:
        org_id = get_organization_slug(organization_slug.strip())
        rows = _fetch_conversation_bookings(org_id, conv_id, future_only=True)
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    bookings = [_map_booking_row(row, tz) for row in rows]
    if not bookings:
        return {
            "status": "ok",
            "bookings": [],
            "message": "No hay citas confirmadas próximas para este contacto.",
        }

    return {
        "status": "ok",
        "bookings": bookings,
        "message": f"{len(bookings)} cita(s) confirmada(s).",
    }


def run_cancel_appointment(
    *,
    organization_slug: str,
    conversation_id: str | None,
    booking_id: str,
    timezone: str = "America/La_Paz",
) -> dict[str, Any]:
    """Soft-cancel a confirmed future booking owned by the conversation."""
    org_err = _validate_org_slug(organization_slug)
    if org_err:
        return org_err

    conv_id = _clean_conversation_id(conversation_id)
    if not conv_id:
        return _no_conversation_error()

    bid = (booking_id or "").strip()
    if not bid:
        return {"status": "error", "message": "Falta booking_id."}

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        return {"status": "error", "message": f"Invalid timezone: {timezone}"}

    try:
        org_id = get_organization_slug(organization_slug.strip())
        row = _fetch_booking_for_mutation(org_id, conv_id, bid)
        if row is None:
            return _not_found_error()

        start_at = _parse_iso(row.get("start_at"))
        if start_at is None or start_at <= datetime.now(UTC):
            return {
                "status": "error",
                "message": "No se puede cancelar una cita pasada.",
            }

        updated = _update_booking_status(org_id, conv_id, bid, "cancelled")
        if updated is None:
            return _not_found_error()
        _sync_booking_reminders(org_id, bid)
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}

    booking = _map_booking_row(updated, tz)
    logger.info("Booking cancelled booking_id=%s conversation_id=%s", bid, conv_id)
    return {
        "status": "cancelled",
        "booking": booking,
        "message": "Cita cancelada. Confirme al cliente.",
    }


def run_reschedule_appointment(
    *,
    organization_slug: str,
    conversation_id: str | None,
    booking_id: str,
    slot_id: str,
    duration_minutes: int | None = None,
    timezone: str = "America/La_Paz",
) -> dict[str, Any]:
    """Move a confirmed future booking to a new slot (in-place update)."""
    org_err = _validate_org_slug(organization_slug)
    if org_err:
        return org_err

    conv_id = _clean_conversation_id(conversation_id)
    if not conv_id:
        return _no_conversation_error()

    bid = (booking_id or "").strip()
    if not bid:
        return {"status": "error", "message": "Falta booking_id."}

    sid = (slot_id or "").strip()
    if not sid:
        return {
            "status": "error",
            "message": "Falta slot_id. Llame list_available_hours primero.",
        }

    parsed = parse_slot_id(sid)
    if parsed is None:
        return {"status": "error", "message": "slot_id inválido."}

    schedule_slug, new_start = parsed

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        return {"status": "error", "message": f"Invalid timezone: {timezone}"}

    try:
        org_id = get_organization_slug(organization_slug.strip())
        row = _fetch_booking_for_mutation(org_id, conv_id, bid)
        if row is None:
            return _not_found_error()

        start_at = _parse_iso(row.get("start_at"))
        if start_at is None or start_at <= datetime.now(UTC):
            return {
                "status": "error",
                "message": "No se puede reagendar una cita pasada.",
            }

        schedules = list_schedules(org_id)
        schedule = _find_schedule_by_slug(schedules, schedule_slug)
        if schedule is None:
            return {
                "status": "error",
                "message": f"Sede/horario inválido para slot_id: {schedule_slug}.",
            }

        minutes = _resolve_duration_minutes(row, schedule, duration_minutes)
        new_end = new_start + timedelta(minutes=minutes)

        updated = _update_booking_times(
            org_id,
            conv_id,
            bid,
            schedule_id=schedule["id"],
            start_at=new_start,
            end_at=new_end,
        )
        if updated is None:
            return _not_found_error()
        _sync_booking_reminders(org_id, bid)
    except RuntimeError as exc:
        message = str(exc)
        if (
            "no longer available" in message.casefold()
            or "disponible" in message.casefold()
        ):
            return {
                "status": "error",
                "message": (
                    "Ese cupo ya no está disponible. Llame "
                    "list_available_hours de nuevo y ofrezca otros horarios."
                ),
            }
        return {"status": "error", "message": message}

    booking = _map_booking_row(updated, tz)
    logger.info(
        "Booking rescheduled booking_id=%s slot_id=%s conversation_id=%s",
        bid,
        sid,
        conv_id,
    )
    return {
        "status": "rescheduled",
        "booking": booking,
        "message": (
            "Cita reagendada. Confirme al cliente con sede, servicio, "
            "fecha y hora. No derive a humano."
        ),
    }


def _sync_booking_reminders(org_id: str, booking_id: str) -> None:
    """Ask Nest to cancel/reschedule reminder jobs after a direct Supabase write."""
    try:
        api_request(
            "POST",
            f"/scheduling/bookings/{booking_id}/reminders/sync",
            body={"organizationId": org_id},
        )
    except Exception:
        logger.warning(
            "Reminder sync failed booking_id=%s org_id=%s",
            booking_id,
            org_id,
            exc_info=True,
        )


def _validate_org_slug(organization_slug: str) -> dict[str, Any] | None:
    if not (organization_slug or "").strip():
        return {"status": "error", "message": "organization_slug cannot be empty"}
    return None


def _clean_conversation_id(conversation_id: str | None) -> str | None:
    cleaned = (conversation_id or "").strip()
    return cleaned or None


def _no_conversation_error() -> dict[str, Any]:
    return {
        "status": "error",
        "message": (
            "No hay conversación vinculada. No se pueden consultar citas "
            "sin conversation_id."
        ),
    }


def _not_found_error() -> dict[str, Any]:
    return {
        "status": "error",
        "message": "Cita no encontrada o no pertenece a esta conversación.",
    }


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_time_12h(local: datetime) -> str:
    hour24 = local.hour
    minute = local.minute
    suffix = "AM" if hour24 < 12 else "PM"
    hour12 = hour24 % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def _weekday_es(local: datetime) -> str:
    return _WEEKDAY_ES[local.weekday()]


def _schedule_embed(row: dict[str, Any]) -> dict[str, Any]:
    schedules = row.get("schedules")
    if isinstance(schedules, dict):
        return schedules
    if isinstance(schedules, list) and schedules and isinstance(schedules[0], dict):
        return schedules[0]
    return {}


def _map_booking_row(row: dict[str, Any], tz: ZoneInfo) -> dict[str, str]:
    schedule = _schedule_embed(row)
    sede = str(schedule.get("name") or "")
    schedule_slug = str(schedule.get("slug") or "")
    schedule_tz_name = schedule.get("timezone")
    display_tz = tz
    if isinstance(schedule_tz_name, str) and schedule_tz_name.strip():
        try:
            display_tz = ZoneInfo(schedule_tz_name.strip())
        except Exception:
            display_tz = tz

    start_raw = str(row.get("start_at") or "")
    start = _parse_iso(start_raw)
    if start is None:
        return {
            "booking_id": str(row.get("id") or ""),
            "sede": sede,
            "schedule_slug": schedule_slug,
            "service_name": str(row.get("service_name") or ""),
            "date": "",
            "weekday": "",
            "time": "",
            "label": "",
        }

    local = start.astimezone(display_tz)
    day = local.date().isoformat()
    time_12h = _format_time_12h(local)
    return {
        "booking_id": str(row.get("id") or ""),
        "sede": sede,
        "schedule_slug": schedule_slug,
        "service_name": str(row.get("service_name") or ""),
        "date": day,
        "weekday": _weekday_es(local),
        "time": time_12h,
        "label": f"{day} {time_12h}",
    }


def _find_schedule_by_slug(
    schedules: Sequence[ScheduleRow],
    slug: str,
) -> ScheduleRow | None:
    needle = slug.casefold()
    for schedule in schedules:
        if schedule.get("slug", "").casefold() == needle:
            return schedule
    return None


def _resolve_duration_minutes(
    row: dict[str, Any],
    schedule: ScheduleRow,
    override: int | None,
) -> int:
    if override is not None:
        try:
            value = int(override)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value

    start = _parse_iso(row.get("start_at"))
    end = _parse_iso(row.get("end_at"))
    if start is not None and end is not None and end > start:
        return max(1, int((end - start).total_seconds() // 60))

    fallback = schedule.get("duration_minutes")
    if isinstance(fallback, int) and fallback > 0:
        return fallback
    return 60


def _now_iso_utc() -> str:
    return datetime.now(UTC).isoformat()


def _get_client():
    from chatty_agent_common.providers.supabase import get_supabase_client

    return get_supabase_client()


def _fetch_conversation_customer_id(
    org_id: str,
    conversation_id: str,
) -> str | None:
    client = _get_client()
    try:
        response = (
            client.table("conversations")
            .select("customer_id")
            .eq("id", conversation_id)
            .eq("organization_id", org_id)
            .maybe_single()
            .execute()
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc

    row = _single_booking_row(response)
    if not row:
        return None
    customer_id = row.get("customer_id")
    return (
        customer_id.strip()
        if isinstance(customer_id, str) and customer_id.strip()
        else None
    )


def _booking_owned_by_conversation(
    row: dict[str, Any],
    *,
    conversation_id: str,
    customer_id: str | None,
) -> bool:
    row_conv = row.get("conversation_id")
    if isinstance(row_conv, str) and row_conv == conversation_id:
        return True
    row_customer = row.get("customer_id")
    return (
        bool(customer_id)
        and isinstance(row_customer, str)
        and row_customer == customer_id
    )


def _fetch_conversation_bookings(
    org_id: str,
    conversation_id: str,
    *,
    future_only: bool,
) -> list[dict[str, Any]]:
    client = _get_client()
    customer_id = _fetch_conversation_customer_id(org_id, conversation_id)
    try:
        query = (
            client.table("bookings")
            .select(_BOOKING_SELECT)
            .eq("organization_id", org_id)
            .eq("status", "confirmed")
            .order("start_at")
        )
        if customer_id:
            query = query.or_(
                f"conversation_id.eq.{conversation_id},customer_id.eq.{customer_id}"
            )
        else:
            query = query.eq("conversation_id", conversation_id)
        if future_only:
            query = query.gt("end_at", _now_iso_utc())
        response = query.execute()
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc

    data = response.data
    if not isinstance(data, list):
        raise RuntimeError("bookings query returned an invalid payload")
    return [row for row in data if isinstance(row, dict)]


def _fetch_booking_for_mutation(
    org_id: str,
    conversation_id: str,
    booking_id: str,
) -> dict[str, Any] | None:
    client = _get_client()
    customer_id = _fetch_conversation_customer_id(org_id, conversation_id)
    try:
        response = (
            client.table("bookings")
            .select(_BOOKING_SELECT)
            .eq("id", booking_id)
            .eq("organization_id", org_id)
            .eq("status", "confirmed")
            .maybe_single()
            .execute()
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc

    row = _single_booking_row(response)
    if row is None:
        return None
    if _booking_owned_by_conversation(
        row,
        conversation_id=conversation_id,
        customer_id=customer_id,
    ):
        return row
    return None


def _update_booking_status(
    org_id: str,
    conversation_id: str,
    booking_id: str,
    status: str,
) -> dict[str, Any] | None:
    client = _get_client()
    _ = conversation_id
    try:
        response = (
            client.table("bookings")
            .update({"status": status})
            .eq("id", booking_id)
            .eq("organization_id", org_id)
            .eq("status", "confirmed")
            .select(_BOOKING_SELECT)
            .execute()
        )
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc

    return _single_booking_row(response)


def _update_booking_times(
    org_id: str,
    conversation_id: str,
    booking_id: str,
    *,
    schedule_id: str,
    start_at: datetime,
    end_at: datetime,
) -> dict[str, Any] | None:
    client = _get_client()
    _ = conversation_id
    payload = {
        "schedule_id": schedule_id,
        "start_at": start_at.astimezone(UTC).isoformat(),
        "end_at": end_at.astimezone(UTC).isoformat(),
        # New appointment time → allow both reminder offsets to fire again.
        "reminder_first_status": "pending",
        "reminder_second_status": "pending",
        "reminder_first_sent_at": None,
        "reminder_second_sent_at": None,
        "reminder_first_claimed_at": None,
        "reminder_second_claimed_at": None,
    }
    try:
        response = (
            client.table("bookings")
            .update(payload)
            .eq("id", booking_id)
            .eq("organization_id", org_id)
            .eq("status", "confirmed")
            .select(_BOOKING_SELECT)
            .execute()
        )
    except APIError as exc:
        if getattr(exc, "code", None) == _EXCLUSION_VIOLATION:
            raise RuntimeError(
                "That slot is no longer available. Check availability again."
            ) from exc
        raise RuntimeError(str(exc)) from exc
    except httpx.ConnectError as exc:
        raise RuntimeError(_CONNECT_ERROR_HINT) from exc

    return _single_booking_row(response)


def _single_booking_row(response: object) -> dict[str, Any] | None:
    data = getattr(response, "data", response)
    if isinstance(data, list):
        first = data[0] if data else None
        return first if isinstance(first, dict) else None
    if isinstance(data, dict):
        return data
    return None
