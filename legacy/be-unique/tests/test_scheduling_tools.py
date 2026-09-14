"""Unit tests for Be Unique scheduling wrappers (catalog resolve + Nest calls)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from app.subagents.customer.tools.scheduling import (
    book_appointment,
    cancel_appointment,
    list_available_days,
    list_available_hours,
    list_my_appointments,
    reschedule_appointment,
)

_SCHEDULES = [
    {
        "id": "s1",
        "name": "Sucre",
        "slug": "sucre",
        "timezone": "America/La_Paz",
        "duration_minutes": 60,
        "is_default": True,
        "is_active": True,
        "max_days_ahead": 14,
    },
    {
        "id": "s2",
        "name": "Cochabamba",
        "slug": "cochabamba",
        "timezone": "America/La_Paz",
        "duration_minutes": 60,
        "is_default": False,
        "is_active": True,
        "max_days_ahead": 14,
    },
]


def _tool_context(
    state: dict[str, Any] | None = None,
    *,
    session_id: str | None = "conv-test-1",
) -> MagicMock:
    ctx = MagicMock()
    ctx.state = state if state is not None else {}
    if session_id is None:
        ctx.session = None
    else:
        ctx.session = MagicMock()
        ctx.session.id = session_id
    return ctx


def _catalog_patches() -> tuple[Any, Any]:
    return (
        patch(
            "app.subagents.customer.tools.scheduling.get_organization_slug",
            return_value="org-1",
        ),
        patch(
            "app.subagents.customer.tools.scheduling.list_schedules",
            return_value=_SCHEDULES,
        ),
    )


@patch("app.subagents.customer.tools.scheduling.run_list_available_days")
def test_list_available_days_unknown_sede_errors(
    mock_run: MagicMock,
) -> None:
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_days("La Paz", _tool_context())
    assert result["status"] == "error"
    assert "Sucre" in result["message"]
    mock_run.assert_not_called()


@patch("app.subagents.customer.tools.scheduling.run_list_available_days")
def test_list_available_days_single_schedule_auto(
    mock_run: MagicMock,
) -> None:
    mock_run.return_value = {
        "status": "ok",
        "available_days": [],
        "slots": [],
        "days": [],
        "message": "none",
    }
    single = [
        {
            "id": "s1",
            "name": "General",
            "slug": "general",
            "timezone": "America/La_Paz",
            "is_default": True,
            "is_active": True,
        }
    ]
    with (
        patch(
            "app.subagents.customer.tools.scheduling.get_organization_slug",
            return_value="org-1",
        ),
        patch(
            "app.subagents.customer.tools.scheduling.list_schedules",
            return_value=single,
        ),
    ):
        result = list_available_days("cualquier-cosa", _tool_context())
    assert result["status"] == "ok"
    assert mock_run.call_args.kwargs["schedule_slug"] == "general"


@patch("app.subagents.customer.tools.scheduling.run_list_available_days")
def test_list_available_days_uses_active_sede_when_empty(
    mock_run: MagicMock,
) -> None:
    mock_run.return_value = {
        "status": "ok",
        "available_days": [],
        "slots": [],
        "days": [],
        "message": "none",
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_days(
            "",
            _tool_context({"active_sede": "Cochabamba"}),
        )
    assert result["status"] == "ok"
    assert mock_run.call_args.kwargs["schedule_slug"] == "cochabamba"


@patch("app.subagents.customer.tools.scheduling.run_list_available_days")
def test_list_available_days_accepts_sede_prefix(
    mock_run: MagicMock,
) -> None:
    mock_run.return_value = {
        "status": "ok",
        "available_days": [],
        "slots": [],
        "days": [],
        "message": "none",
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_days("sede_sucre", _tool_context())
    assert result["status"] == "ok"
    assert mock_run.call_args.kwargs["schedule_slug"] == "sucre"


@patch("app.subagents.customer.tools.scheduling.run_list_available_days")
def test_list_available_days_returns_days_without_slots(
    mock_run: MagicMock,
) -> None:
    mock_run.return_value = {
        "status": "ok",
        "available_days": [{"date": "2026-08-06", "weekday": "Jueves"}],
        "slots": [],
        "days": [],
        "message": "1 día(s) con cupos: Jueves.",
    }
    ctx = _tool_context()
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_days(
            "Sucre",
            ctx,
            service_name="Limpieza facial",
            duration_minutes=60,
        )

    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["organization_slug"] == "be-unique"
    assert kwargs["schedule_slug"] == "sucre"
    assert kwargs["duration_minutes"] == 60
    assert kwargs["timezone"] == "America/La_Paz"
    assert result["status"] == "ok"
    assert result["sede"] == "Sucre"
    assert result["available_days"] == [
        {"date": "2026-08-06", "weekday": "Jueves"},
    ]
    assert result["slots"] == []
    assert result["days"] == []
    assert ctx.state["active_sede"] == "Sucre"
    assert ctx.state["active_service_name"] == "Limpieza facial"
    assert ctx.state["active_duration_minutes"] == 60


@patch("app.subagents.customer.tools.scheduling.run_list_available_days")
def test_list_available_days_without_duration(mock_run: MagicMock) -> None:
    mock_run.return_value = {
        "status": "ok",
        "available_days": [],
        "slots": [],
        "days": [],
        "message": "none",
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        list_available_days("Cochabamba", _tool_context())
    assert mock_run.call_args.kwargs["schedule_slug"] == "cochabamba"
    assert mock_run.call_args.kwargs["duration_minutes"] is None


@patch("app.subagents.customer.tools.scheduling.run_list_available_hours")
def test_list_available_hours_forwards_date(mock_run: MagicMock) -> None:
    slot = {
        "slot_id": "sucre|2026-08-06T13:00:00Z",
        "date": "2026-08-06",
        "time": "9:00 AM",
        "period": "morning",
        "label": "2026-08-06 9:00 AM",
    }
    mock_run.return_value = {
        "status": "ok",
        "slots": [slot],
        "days": [
            {
                "date": "2026-08-06",
                "weekday": "Jueves",
                "slots": [slot],
            }
        ],
        "available_days": [{"date": "2026-08-06", "weekday": "Jueves"}],
        "slot_count": 1,
        "period_counts": {"morning": 1, "afternoon": 0, "evening": 0},
        "needs_period_filter": False,
        "truncated": False,
        "message": "Cupos para Jueves 2026-08-06: 1 horario(s).",
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_hours(
            "Sucre",
            "2026-08-06",
            _tool_context({"active_duration_minutes": 30}),
            service_name="Depilación",
        )

    assert mock_run.call_args.kwargs["date"] == "2026-08-06"
    assert mock_run.call_args.kwargs["duration_minutes"] == 30
    assert mock_run.call_args.kwargs["period"] is None
    assert mock_run.call_args.kwargs["max_days_ahead"] == 14
    assert result["status"] == "ok"
    assert result["slots"][0]["sede"] == "Sucre"
    assert result["slots"][0]["time"] == "9:00 AM"
    assert result["days"][0]["slots"][0]["sede"] == "Sucre"
    assert result["needs_period_filter"] is False
    assert result["slot_count"] == 1
    assert "delivery_hint" not in result


@patch("app.subagents.customer.tools.scheduling.run_list_available_hours")
def test_list_available_hours_forwards_period(mock_run: MagicMock) -> None:
    slot = {
        "slot_id": "sucre|2026-08-06T19:00:00Z",
        "date": "2026-08-06",
        "time": "3:00 PM",
        "period": "afternoon",
        "label": "2026-08-06 3:00 PM",
    }
    mock_run.return_value = {
        "status": "ok",
        "slots": [slot],
        "days": [
            {
                "date": "2026-08-06",
                "weekday": "Jueves",
                "slots": [slot],
            }
        ],
        "available_days": [{"date": "2026-08-06", "weekday": "Jueves"}],
        "slot_count": 12,
        "period_counts": {"morning": 4, "afternoon": 6, "evening": 2},
        "needs_period_filter": False,
        "truncated": False,
        "message": "Cupos (franja afternoon).",
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_hours(
            "Sucre",
            "2026-08-06",
            _tool_context(),
            period="afternoon",
        )

    assert mock_run.call_args.kwargs["period"] == "afternoon"
    assert result["slots"][0]["time"] == "3:00 PM"
    assert result["period_counts"]["afternoon"] == 6


@patch("app.subagents.customer.tools.scheduling.run_list_available_hours")
def test_list_available_hours_propagates_needs_period_filter(
    mock_run: MagicMock,
) -> None:
    mock_run.return_value = {
        "status": "ok",
        "slots": [],
        "days": [
            {
                "date": "2026-08-06",
                "weekday": "Jueves",
                "slots": [],
            }
        ],
        "available_days": [{"date": "2026-08-06", "weekday": "Jueves"}],
        "slot_count": 14,
        "period_counts": {"morning": 6, "afternoon": 5, "evening": 3},
        "needs_period_filter": True,
        "truncated": False,
        "message": "14 horario(s). Pregunte franja.",
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_hours("Sucre", "2026-08-06", _tool_context())

    assert result["status"] == "ok"
    assert result["needs_period_filter"] is True
    assert result["slots"] == []
    assert result["slot_count"] == 14
    assert result["period_counts"]["morning"] == 6
    assert "No hay cupos" not in result["message"]


@patch("app.subagents.customer.tools.scheduling.run_list_available_hours")
def test_list_available_hours_forwards_past_error_code(mock_run: MagicMock) -> None:
    mock_run.return_value = {
        "status": "error",
        "error_code": "past",
        "date": "2020-01-01",
        "message": "Date is in the past.",
        "slots": [],
        "days": [],
        "available_days": [],
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_hours("Sucre", "2020-01-01", _tool_context())
    assert result["status"] == "error"
    assert result["error_code"] == "past"
    assert result["date"] == "2020-01-01"


@patch("app.subagents.customer.tools.scheduling.run_list_available_days")
def test_list_available_days_forwards_from_to(mock_run: MagicMock) -> None:
    mock_run.return_value = {
        "status": "ok",
        "available_days": [],
        "from_date": "2026-08-27",
        "to_date": "2026-09-03",
        "slots": [],
        "days": [],
        "message": "none",
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_days(
            "Sucre",
            _tool_context(),
            from_date="2026-08-27",
            to_date="2026-09-03",
        )
    assert mock_run.call_args.kwargs["from_date"] == "2026-08-27"
    assert mock_run.call_args.kwargs["to_date"] == "2026-09-03"
    assert result["from_date"] == "2026-08-27"
    assert result["to_date"] == "2026-09-03"


@patch("app.subagents.customer.tools.scheduling.run_list_available_hours")
def test_list_available_hours_forwards_availability_kind(mock_run: MagicMock) -> None:
    mock_run.return_value = {
        "status": "ok",
        "availability_kind": "empty_day",
        "date": "2026-08-27",
        "horizon_end": "2026-09-05",
        "slots": [],
        "days": [],
        "available_days": [],
        "slot_count": 0,
        "period_counts": {"morning": 0, "afternoon": 0, "evening": 0},
        "needs_period_filter": False,
        "truncated": False,
        "message": "No open slots in the requested window. Try another date.",
    }
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_available_hours("Sucre", "2026-08-27", _tool_context())
    assert result["availability_kind"] == "empty_day"
    assert result["date"] == "2026-08-27"
    assert result["horizon_end"] == "2026-09-05"


@patch("app.subagents.customer.tools.scheduling.run_book_appointment")
def test_book_appointment_posts_domain_metadata(mock_run: MagicMock) -> None:
    mock_run.return_value = {
        "status": "booked",
        "booking": {
            "booking_id": "bk-123",
            "slot_id": "sucre|x",
            "label": "2026-08-06 09:00",
        },
    }
    ctx = _tool_context({"active_duration_minutes": 30})
    org, schedules = _catalog_patches()
    with org, schedules:
        booked = book_appointment(
            sede="Sucre",
            customer_name="María Pérez",
            service_name="Depilación axilas",
            slot_id="sucre|2026-08-06T13:00:00Z",
            tool_context=ctx,
        )

    assert booked["status"] == "booked"
    assert booked["booking"]["booking_id"] == "bk-123"
    assert booked["booking"]["sede"] == "Sucre"
    assert ctx.state["last_booking_id"] == "bk-123"
    assert ctx.state["customer_name"] == "María Pérez"
    kwargs = mock_run.call_args.kwargs
    assert kwargs["metadata"]["sede"] == "Sucre"
    assert kwargs["metadata"]["service_name"] == "Depilación axilas"
    assert kwargs["service_name"] == "Depilación axilas"
    assert kwargs["duration_minutes"] == 30
    assert kwargs["timezone"] == "America/La_Paz"
    assert kwargs["conversation_id"] == "conv-test-1"


@patch(
    "app.subagents.customer.tools.scheduling.run_book_appointment",
    return_value={
        "status": "error",
        "message": "That slot is no longer available. Check availability again.",
    },
)
def test_book_appointment_conflict_message(_mock_run: MagicMock) -> None:
    org, schedules = _catalog_patches()
    with org, schedules:
        result = book_appointment(
            sede="Sucre",
            customer_name="María",
            service_name="Depilación",
            slot_id="sucre|2026-08-06T13:00:00Z",
            tool_context=_tool_context(),
        )
    assert result["status"] == "error"
    assert "disponible" in result["message"].casefold()
    assert "list_available_hours" in result["message"]


def test_book_appointment_missing_name() -> None:
    org, schedules = _catalog_patches()
    with org, schedules:
        result = book_appointment(
            sede="Sucre",
            customer_name="  ",
            service_name="axila",
            slot_id="sucre|x",
            tool_context=_tool_context(),
        )
    assert result["status"] == "error"
    assert "nombre" in result["message"].casefold()


def test_book_appointment_wrong_slot_sede() -> None:
    org, schedules = _catalog_patches()
    with org, schedules:
        result = book_appointment(
            sede="Sucre",
            customer_name="María",
            service_name="Depilación",
            slot_id="cochabamba|2026-08-06T13:00:00Z",
            tool_context=_tool_context(),
        )
    assert result["status"] == "error"
    assert "no corresponde" in result["message"].casefold()


@patch("app.subagents.customer.tools.scheduling.run_list_conversation_bookings")
def test_list_my_appointments_forwards_conversation(mock_run: MagicMock) -> None:
    mock_run.return_value = {
        "status": "ok",
        "bookings": [
            {
                "booking_id": "bk-1",
                "sede": "Sucre",
                "schedule_slug": "sucre",
                "service_name": "Valoración",
                "date": "2026-08-20",
                "weekday": "Jueves",
                "time": "10:00 AM",
                "label": "2026-08-20 10:00 AM",
            }
        ],
        "message": "1 cita(s) confirmada(s).",
    }
    ctx = _tool_context()
    org, schedules = _catalog_patches()
    with org, schedules:
        result = list_my_appointments(ctx)

    assert result["status"] == "ok"
    assert result["bookings"][0]["booking_id"] == "bk-1"
    kwargs = mock_run.call_args.kwargs
    assert kwargs["organization_slug"] == "be-unique"
    assert kwargs["conversation_id"] == "conv-test-1"
    assert kwargs["timezone"] == "America/La_Paz"
    assert ctx.state["active_sede"] == "Sucre"
    assert ctx.state["active_schedule_slug"] == "sucre"
    assert ctx.state["active_service_name"] == "Valoración"


def test_list_my_appointments_without_conversation() -> None:
    result = list_my_appointments(_tool_context(session_id=None))
    assert result["status"] == "error"
    assert result["bookings"] == []
    assert "conversación" in result["message"].casefold()


@patch("app.subagents.customer.tools.scheduling.run_cancel_appointment")
def test_cancel_appointment_clears_last_booking(mock_run: MagicMock) -> None:
    mock_run.return_value = {
        "status": "cancelled",
        "booking": {
            "booking_id": "bk-99",
            "sede": "Sucre",
            "service_name": "Depilación",
            "label": "2026-08-06 9:00 AM",
        },
    }
    ctx = _tool_context({"last_booking_id": "bk-99", "last_booking_label": "x"})
    org, schedules = _catalog_patches()
    with org, schedules:
        result = cancel_appointment("bk-99", ctx)

    assert result["status"] == "cancelled"
    assert mock_run.call_args.kwargs["booking_id"] == "bk-99"
    assert mock_run.call_args.kwargs["conversation_id"] == "conv-test-1"
    assert ctx.state["last_booking_id"] == ""


@patch("app.subagents.customer.tools.scheduling.run_reschedule_appointment")
def test_reschedule_appointment_updates_state(mock_run: MagicMock) -> None:
    mock_run.return_value = {
        "status": "rescheduled",
        "booking": {
            "booking_id": "bk-1",
            "sede": "Cochabamba",
            "schedule_slug": "cochabamba",
            "service_name": "Valoración",
            "label": "2026-08-21 3:00 PM",
        },
    }
    ctx = _tool_context({"active_duration_minutes": 45})
    org, schedules = _catalog_patches()
    with org, schedules:
        result = reschedule_appointment(
            "bk-1",
            "cochabamba|2026-08-21T19:00:00Z",
            ctx,
        )

    assert result["status"] == "rescheduled"
    kwargs = mock_run.call_args.kwargs
    assert kwargs["booking_id"] == "bk-1"
    assert kwargs["slot_id"] == "cochabamba|2026-08-21T19:00:00Z"
    assert kwargs["duration_minutes"] == 45
    assert kwargs["conversation_id"] == "conv-test-1"
    assert ctx.state["last_booking_id"] == "bk-1"
    assert ctx.state["active_sede"] == "Cochabamba"
    assert ctx.state["active_schedule_slug"] == "cochabamba"


def test_reschedule_appointment_missing_slot_id() -> None:
    org, schedules = _catalog_patches()
    with org, schedules:
        result = reschedule_appointment("bk-1", "  ", _tool_context())
    assert result["status"] == "error"
    assert "slot_id" in result["message"].casefold()
