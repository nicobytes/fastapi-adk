"""Be Unique scheduling ADK tools — thin wrappers over chatty-agent-common."""

from __future__ import annotations

from typing import Any, TypeGuard

from google.adk.tools.tool_context import ToolContext

from chatty_agent_common.playground_session import playground_conversation_id
from chatty_agent_common.providers.supabase import get_organization_slug
from chatty_agent_common.scheduling import (
    ScheduleRow,
    list_schedules,
    resolve_schedule,
    run_book_appointment,
    run_cancel_appointment,
    run_list_available_days,
    run_list_available_hours,
    run_list_conversation_bookings,
    run_reschedule_appointment,
)

_ORG_SLUG = "be-unique"

__all__ = [
    "book_appointment",
    "cancel_appointment",
    "list_available_days",
    "list_available_hours",
    "list_my_appointments",
    "reschedule_appointment",
]


def _error(message: str) -> dict[str, Any]:
    return {"status": "error", "message": message}


def _load_schedules() -> list[ScheduleRow] | dict[str, Any]:
    try:
        org_id = get_organization_slug(_ORG_SLUG)
        return list_schedules(org_id)
    except Exception as exc:
        return _error(f"No se pudo cargar el catálogo de agenda: {exc}")


def _is_error(value: object) -> TypeGuard[dict[str, Any]]:
    return isinstance(value, dict) and value.get("status") == "error"


def _conversation_id(tool_context: ToolContext) -> str | None:
    return playground_conversation_id(tool_context)


def _sede_from_context(tool_context: ToolContext | None) -> str:
    if tool_context is None:
        return ""
    for key in ("active_sede", "active_schedule_slug"):
        value = tool_context.state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _resolve_schedule_row(
    sede: str,
    tool_context: ToolContext | None = None,
) -> ScheduleRow | dict[str, Any]:
    schedules = _load_schedules()
    if isinstance(schedules, dict):
        return schedules

    cleaned = (sede or "").strip()
    if not cleaned:
        cleaned = _sede_from_context(tool_context)

    schedule, schedule_error = resolve_schedule(schedules, cleaned)
    if schedule is None:
        return _error(schedule_error or "Sede inválida.")
    return schedule


def _normalize_duration(duration_minutes: int | None) -> int | None:
    if duration_minutes is None:
        return None
    try:
        value = int(duration_minutes)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _with_sede(items: list[Any], sede: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if "slots" in item and isinstance(item["slots"], list):
            out.append(
                {
                    **item,
                    "slots": [
                        {**slot, "sede": sede}
                        for slot in item["slots"]
                        if isinstance(slot, dict)
                    ],
                }
            )
        else:
            out.append({**item, "sede": sede})
    return out


def list_available_days(
    sede: str,
    tool_context: ToolContext,
    service_name: str | None = None,
    duration_minutes: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """List calendar days with open slots (phase 1 — days only).

    Call when the client accepts a valuation / asks for an appointment and has
    **not** chosen a day yet. Do **not** invent days — only offer dates from
    ``available_days``. Never offer HH:MM from this tool (it returns no slots).

    Optional ``from_date`` / ``to_date`` (``YYYY-MM-DD``, inclusive) anchor
    discovery after ``list_available_hours`` returns ``availability_kind``
    ``empty_day`` or ``beyond_horizon``.

    Before calling, load the relevant skill (``depilacion-laser`` or
    ``faciales``) and pass ``duration_minutes`` = **Tiempo total** from the
    tarifario (initial valuation ≈ 30 min). Omit to use the schedule fallback.

    When the client has **not** named a date, call without ``from_date``.
    When they already named a day, use ``list_available_hours`` first — do not
    require that day to appear in the last **lista corta de descubrimiento**.

    Args:
        sede: Schedule name or slug from the org catalog (e.g. Sucre, cochabamba).
        service_name: Optional service label (e.g. Depilación, Limpieza facial).
        duration_minutes: Optional duration from the loaded skill (Tiempo total / ~30 min valuation); omit to use schedule fallback.
        from_date: Optional start of discovery (inclusive calendar day).
        to_date: Optional end of a named window (inclusive calendar day).
    """
    schedule = _resolve_schedule_row(sede, tool_context)
    if _is_error(schedule):
        return {**schedule, "slots": [], "days": [], "available_days": []}  # type: ignore[arg-type]

    duration = _normalize_duration(duration_minutes)
    result = run_list_available_days(
        organization_slug=_ORG_SLUG,
        schedule_slug=schedule["slug"],
        duration_minutes=duration,
        from_date=from_date,
        to_date=to_date,
        timezone=schedule["timezone"],
    )

    tool_context.state["active_sede"] = schedule["name"]
    tool_context.state["active_schedule_slug"] = schedule["slug"]
    if service_name and str(service_name).strip():
        tool_context.state["active_service_name"] = str(service_name).strip()
    if duration is not None:
        tool_context.state["active_duration_minutes"] = duration

    if result.get("status") != "ok":
        return {
            "status": "error",
            "error_code": result.get("error_code", "api_failure"),
            "message": result.get("message", "Error al consultar disponibilidad."),
            "from_date": result.get("from_date"),
            "to_date": result.get("to_date"),
            "slots": [],
            "days": [],
            "available_days": [],
        }

    available_days = [
        {"date": d["date"], "weekday": d["weekday"]}
        for d in result.get("available_days", [])
        if isinstance(d, dict) and d.get("date") and d.get("weekday")
    ]
    sede_name = schedule["name"]
    if not available_days:
        return {
            "status": "ok",
            "sede": sede_name,
            "available_days": [],
            "from_date": result.get("from_date"),
            "to_date": result.get("to_date"),
            "days": [],
            "slots": [],
            "message": (
                "No hay cupos disponibles en la ventana consultada. Pruebe otra fecha."
            ),
        }

    return {
        "status": "ok",
        "sede": sede_name,
        "available_days": available_days,
        "from_date": result.get("from_date"),
        "to_date": result.get("to_date"),
        "days": [],
        "slots": [],
        "message": str(
            result.get("message") or f"{len(available_days)} día(s) con cupos."
        ),
    }


def list_available_hours(
    sede: str,
    date: str,
    tool_context: ToolContext,
    service_name: str | None = None,
    duration_minutes: int | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    """List open times for one calendar day (hours).

    ``date`` is ``YYYY-MM-DD`` for the day the client named or picked. It **does
    not** have to appear in the last **lista corta de descubrimiento**
    (``available_days`` from a prior ``list_available_days``). Use session
    ``current_date`` only to interpret hoy/mañana/viernes into ``date`` — never
    pass raw ``current_date`` unless the client meant today.

    Branch on ``availability_kind`` (ok) or ``error_code`` (error), not on
    ``message`` text. After ``empty_day`` → ``list_available_days(from_date=date)``.
    After ``beyond_horizon`` → ``list_available_days`` with
    ``from_date = max(today, horizon_end - max_days + 1)`` (default 5).

    Each slot includes ``time`` (12h AM/PM) and ``period``. If
    ``needs_period_filter`` is true, ask morning/afternoon/evening and re-call
    with ``period``.

    Args:
        sede: Schedule name or slug from the org catalog.
        date: Required YYYY-MM-DD for the day to consult.
        service_name: Optional service label.
        duration_minutes: Optional duration from the loaded skill (Tiempo total / ~30 min valuation); omit to use schedule fallback.
        period: Optional ``morning`` / ``afternoon`` / ``evening`` after fringe choice.
    """
    schedule = _resolve_schedule_row(sede, tool_context)
    if _is_error(schedule):
        return {**schedule, "slots": [], "days": [], "available_days": []}  # type: ignore[arg-type]

    duration = _normalize_duration(duration_minutes)
    if duration is None:
        stored = tool_context.state.get("active_duration_minutes")
        duration = _normalize_duration(stored if isinstance(stored, int) else None)

    cleaned_period = (period or "").strip().lower() or None
    result = run_list_available_hours(
        organization_slug=_ORG_SLUG,
        schedule_slug=schedule["slug"],
        date=date,
        duration_minutes=duration,
        timezone=schedule["timezone"],
        period=cleaned_period,
        max_days_ahead=schedule.get("max_days_ahead"),
    )

    tool_context.state["active_sede"] = schedule["name"]
    tool_context.state["active_schedule_slug"] = schedule["slug"]
    if service_name and str(service_name).strip():
        tool_context.state["active_service_name"] = str(service_name).strip()
    if duration is not None:
        tool_context.state["active_duration_minutes"] = duration

    sede_name = schedule["name"]
    tag_fields = {
        "date": result.get("date"),
        "availability_kind": result.get("availability_kind"),
        "error_code": result.get("error_code"),
        "horizon_end": result.get("horizon_end"),
    }

    if result.get("status") != "ok":
        return {
            "status": "error",
            **tag_fields,
            "message": result.get("message", "Error al consultar horarios."),
            "slots": [],
            "days": [],
            "available_days": [],
            "slot_count": 0,
            "period_counts": {"morning": 0, "afternoon": 0, "evening": 0},
            "needs_period_filter": False,
            "truncated": False,
            "sede": sede_name,
        }

    slots = _with_sede(
        [s for s in result.get("slots", []) if isinstance(s, dict)],
        sede_name,
    )
    days = _with_sede(
        [d for d in result.get("days", []) if isinstance(d, dict)],
        sede_name,
    )
    available_days = [
        {"date": d["date"], "weekday": d["weekday"]}
        for d in result.get("available_days", [])
        if isinstance(d, dict) and d.get("date") and d.get("weekday")
    ]
    period_counts = result.get("period_counts") or {
        "morning": 0,
        "afternoon": 0,
        "evening": 0,
    }
    needs_period_filter = bool(result.get("needs_period_filter"))
    truncated = bool(result.get("truncated"))
    slot_count = int(result.get("slot_count") or len(slots))

    return {
        "status": "ok",
        "sede": sede_name,
        **tag_fields,
        "slots": slots,
        "days": days,
        "available_days": available_days,
        "slot_count": slot_count,
        "period_counts": period_counts,
        "needs_period_filter": needs_period_filter,
        "truncated": truncated,
        "message": str(
            result.get("message") or f"{len(slots)} horario(s) disponibles."
        ),
    }


def book_appointment(
    sede: str,
    customer_name: str,
    service_name: str,
    slot_id: str,
    tool_context: ToolContext,
    duration_minutes: int | None = None,
) -> dict[str, Any]:
    """Book an appointment via Chatty NestJS API.

    Call only after the customer picks a slot_id from ``list_available_hours``.
    Does **not** trigger human handoff.

    Args:
        sede: Schedule name or slug from the org catalog
        customer_name: Full name already collected
        service_name: Service label (e.g. Depilación axilas)
        slot_id: Exact id from list_available_hours
        duration_minutes: Optional duration from the loaded skill (Tiempo total / ~30 min valuation); omit to use schedule fallback.
    """
    schedule = _resolve_schedule_row(sede, tool_context)
    if _is_error(schedule):
        return schedule  # type: ignore[return-value]

    name = (customer_name or "").strip()
    service = (service_name or "").strip()
    sid = (slot_id or "").strip()

    if not name:
        return {"status": "error", "message": "Falta el nombre del cliente."}
    if not service:
        return {"status": "error", "message": "Falta el nombre del servicio."}
    if not sid:
        return {
            "status": "error",
            "message": "Falta slot_id. Llame list_available_hours primero.",
        }

    schedule_slug = schedule["slug"]
    # Nest slot ids are scheduleSlug|ISO-start
    if "|" in sid:
        slug_prefix = sid.split("|", 1)[0]
        if slug_prefix != schedule_slug:
            return {
                "status": "error",
                "message": (
                    f"El slot no corresponde a {schedule['name']}. "
                    "Consulte disponibilidad de la sede correcta."
                ),
            }

    duration = _normalize_duration(duration_minutes)
    if duration is None:
        stored = tool_context.state.get("active_duration_minutes")
        duration = _normalize_duration(stored if isinstance(stored, int) else None)

    result = run_book_appointment(
        organization_slug=_ORG_SLUG,
        schedule_slug=schedule_slug,
        service_name=service,
        slot_id=sid,
        duration_minutes=duration,
        conversation_id=_conversation_id(tool_context),
        metadata={
            "customer_name": name,
            "service_name": service,
            "sede": schedule["name"],
        },
        timezone=schedule["timezone"],
    )

    if result.get("status") != "booked":
        message = str(result.get("message") or "Error al reservar.")
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

    booking = result.get("booking") or {}
    booking_id = str(booking.get("booking_id") or "")
    label = str(booking.get("label") or "")

    tool_context.state["active_sede"] = schedule["name"]
    tool_context.state["active_schedule_slug"] = schedule_slug
    tool_context.state["customer_name"] = name
    tool_context.state["active_service_name"] = service
    if duration is not None:
        tool_context.state["active_duration_minutes"] = duration
    tool_context.state["last_booking_id"] = booking_id
    tool_context.state["last_booking_label"] = label

    return {
        "status": "booked",
        "booking": {
            "booking_id": booking_id,
            "slot_id": sid,
            "sede": schedule["name"],
            "label": label,
            "customer_name": name,
            "service_name": service,
        },
        "message": (
            "Cita reservada. Confirme al cliente con sede, nombre, "
            "servicio, fecha y hora. No derive a humano."
        ),
    }


def list_my_appointments(tool_context: ToolContext) -> dict[str, Any]:
    """List confirmed upcoming appointments for this WhatsApp conversation.

    Call when the client asks to see, change, or cancel an existing appointment.
    Never invent appointments from chat history — only rows from this tool.

    Returns ``bookings`` with ``booking_id``, ``sede``, ``service_name``, ``date``,
    ``weekday``, ``time``, and ``label``. Use ``booking_id`` for cancel/reschedule.
    """
    conv_id = _conversation_id(tool_context)
    if not conv_id:
        return {
            "status": "error",
            "message": ("No hay conversación vinculada. No se pueden consultar citas."),
            "bookings": [],
        }

    schedule = _resolve_schedule_row("", tool_context)
    tz = "America/La_Paz"
    if not _is_error(schedule):
        tz = schedule["timezone"]

    result = run_list_conversation_bookings(
        organization_slug=_ORG_SLUG,
        conversation_id=conv_id,
        timezone=tz,
    )

    if result.get("status") == "ok" and result.get("bookings"):
        first = result["bookings"][0]
        if isinstance(first, dict):
            tool_context.state["active_sede"] = first.get("sede") or ""
            slug = first.get("schedule_slug")
            if isinstance(slug, str) and slug.strip():
                tool_context.state["active_schedule_slug"] = slug.strip()
            service = first.get("service_name")
            if isinstance(service, str) and service.strip():
                tool_context.state["active_service_name"] = service.strip()

    return result


def cancel_appointment(
    booking_id: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Cancel a confirmed upcoming appointment for this conversation.

    Call only after ``list_my_appointments`` and explicit client confirmation.
    Does **not** trigger human handoff.

    Args:
        booking_id: Exact id from ``list_my_appointments``.
    """
    conv_id = _conversation_id(tool_context)
    if not conv_id:
        return {
            "status": "error",
            "message": "No hay conversación vinculada.",
        }

    schedule = _resolve_schedule_row("", tool_context)
    tz = "America/La_Paz"
    if not _is_error(schedule):
        tz = schedule["timezone"]

    result = run_cancel_appointment(
        organization_slug=_ORG_SLUG,
        conversation_id=conv_id,
        booking_id=booking_id,
        timezone=tz,
    )

    if result.get("status") == "cancelled":
        booking = result.get("booking") or {}
        if isinstance(booking, dict):
            bid = str(booking.get("booking_id") or "")
            if bid and tool_context.state.get("last_booking_id") == bid:
                tool_context.state["last_booking_id"] = ""
                tool_context.state["last_booking_label"] = ""

    return result


def reschedule_appointment(
    booking_id: str,
    slot_id: str,
    tool_context: ToolContext,
    duration_minutes: int | None = None,
) -> dict[str, Any]:
    """Reschedule an existing appointment to a new slot from ``list_available_hours``.

    Call only after the client picks ``booking_id`` (from ``list_my_appointments``)
    and ``slot_id`` (from ``list_available_hours``). Does **not** trigger handoff.

    Args:
        booking_id: Exact id from ``list_my_appointments``.
        slot_id: Exact id from ``list_available_hours``.
        duration_minutes: Optional duration from the loaded skill (Tiempo total / ~30 min valuation); omit to keep booking length.
    """
    conv_id = _conversation_id(tool_context)
    if not conv_id:
        return {
            "status": "error",
            "message": "No hay conversación vinculada.",
        }

    bid = (booking_id or "").strip()
    sid = (slot_id or "").strip()
    if not bid:
        return {"status": "error", "message": "Falta booking_id."}
    if not sid:
        return {
            "status": "error",
            "message": "Falta slot_id. Llame list_available_hours primero.",
        }

    schedule = _resolve_schedule_row("", tool_context)
    tz = "America/La_Paz"
    if not _is_error(schedule):
        tz = schedule["timezone"]

    duration = _normalize_duration(duration_minutes)
    if duration is None:
        stored = tool_context.state.get("active_duration_minutes")
        duration = _normalize_duration(stored if isinstance(stored, int) else None)

    result = run_reschedule_appointment(
        organization_slug=_ORG_SLUG,
        conversation_id=conv_id,
        booking_id=bid,
        slot_id=sid,
        duration_minutes=duration,
        timezone=tz,
    )

    if result.get("status") == "rescheduled":
        booking = result.get("booking") or {}
        if isinstance(booking, dict):
            tool_context.state["last_booking_id"] = str(
                booking.get("booking_id") or bid
            )
            tool_context.state["last_booking_label"] = str(booking.get("label") or "")
            sede = booking.get("sede")
            if isinstance(sede, str) and sede.strip():
                tool_context.state["active_sede"] = sede.strip()
            slug = booking.get("schedule_slug")
            if isinstance(slug, str) and slug.strip():
                tool_context.state["active_schedule_slug"] = slug.strip()
            service = booking.get("service_name")
            if isinstance(service, str) and service.strip():
                tool_context.state["active_service_name"] = service.strip()

    return result
