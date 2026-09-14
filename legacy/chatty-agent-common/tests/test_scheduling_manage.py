"""Unit tests for booking list/cancel/reschedule via Supabase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from postgrest.exceptions import APIError

from chatty_agent_common.scheduling.manage import (
    _sync_booking_reminders,
    parse_slot_id,
    run_cancel_appointment,
    run_list_conversation_bookings,
    run_reschedule_appointment,
)

_TZ = ZoneInfo("America/La_Paz")
_ORG_SLUG = "be-unique"
_CONV_ID = "conv-abc"
_BOOKING_ID = "bk-1"
_FUTURE_START = datetime.now(UTC) + timedelta(days=2)
_FUTURE_END = _FUTURE_START + timedelta(minutes=60)
_FUTURE_ISO = _FUTURE_START.isoformat()
_FUTURE_END_ISO = _FUTURE_END.isoformat()

_SCHEDULES = [
    {
        "id": "sched-1",
        "name": "Sucre",
        "slug": "sucre",
        "timezone": "America/La_Paz",
        "duration_minutes": 60,
        "is_default": True,
        "is_active": True,
    }
]

_BOOKING_ROW = {
    "id": _BOOKING_ID,
    "service_name": "Depilación axilas",
    "start_at": _FUTURE_ISO,
    "end_at": _FUTURE_END_ISO,
    "status": "confirmed",
    "schedule_id": "sched-1",
    "schedules": {
        "name": "Sucre",
        "slug": "sucre",
        "timezone": "America/La_Paz",
        "duration_minutes": 60,
    },
}


def _chain(*, execute_data: object) -> MagicMock:
    chain = MagicMock()
    for method in (
        "select",
        "eq",
        "gt",
        "or_",
        "order",
        "update",
        "maybe_single",
    ):
        getattr(chain, method).return_value = chain
    chain.execute.return_value = MagicMock(data=execute_data)
    return chain


def test_parse_slot_id_valid() -> None:
    start = "2026-08-06T13:00:00Z"
    parsed = parse_slot_id(f"sucre|{start}")
    assert parsed is not None
    slug, dt = parsed
    assert slug == "sucre"
    assert dt.isoformat().startswith("2026-08-06")


def test_parse_slot_id_invalid() -> None:
    assert parse_slot_id("") is None
    assert parse_slot_id("sucre") is None


@patch("chatty_agent_common.scheduling.manage._get_client")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_list_conversation_bookings_empty(
    _mock_org: object,
    mock_client: MagicMock,
) -> None:
    table = MagicMock()
    mock_client.return_value.table.return_value = table
    table.select.return_value = _chain(execute_data=[])

    result = run_list_conversation_bookings(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert result["bookings"] == []
    assert "para este contacto" in result["message"]


@patch("chatty_agent_common.scheduling.manage._get_client")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_list_conversation_bookings_maps_rows(
    _mock_org: object,
    mock_client: MagicMock,
) -> None:
    table = MagicMock()
    mock_client.return_value.table.return_value = table
    table.select.return_value = _chain(execute_data=[_BOOKING_ROW])

    result = run_list_conversation_bookings(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert len(result["bookings"]) == 1
    booking = result["bookings"][0]
    assert booking["booking_id"] == _BOOKING_ID
    assert booking["sede"] == "Sucre"
    assert booking["service_name"] == "Depilación axilas"
    assert booking["time"]


def test_list_requires_conversation_id() -> None:
    result = run_list_conversation_bookings(
        organization_slug=_ORG_SLUG,
        conversation_id=None,
    )
    assert result["status"] == "error"
    assert "conversación" in result["message"].casefold()


@patch("chatty_agent_common.scheduling.manage._get_client")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_list_includes_customer_scoped_bookings(
    _mock_org: object,
    mock_client: MagicMock,
) -> None:
    conv_chain = _chain(execute_data={"customer_id": "cust-1"})
    book_chain = _chain(
        execute_data=[
            {
                **_BOOKING_ROW,
                "conversation_id": None,
                "customer_id": "cust-1",
            }
        ]
    )

    def table(name: str) -> MagicMock:
        mocked = MagicMock()
        mocked.select.return_value = (
            conv_chain if name == "conversations" else book_chain
        )
        return mocked

    mock_client.return_value.table.side_effect = table

    result = run_list_conversation_bookings(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert len(result["bookings"]) == 1
    assert result["bookings"][0]["booking_id"] == _BOOKING_ID
    book_chain.eq.assert_any_call("organization_id", "org-1")
    book_chain.or_.assert_called_once()
    filter_arg = book_chain.or_.call_args[0][0]
    assert "customer_id.eq.cust-1" in filter_arg
    assert f"conversation_id.eq.{_CONV_ID}" in filter_arg
    book_chain.gt.assert_called()
    assert book_chain.gt.call_args[0][0] == "end_at"


@patch("chatty_agent_common.scheduling.manage._get_client")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_list_in_progress_included_ended_excluded_via_end_at(
    _mock_org: object,
    mock_client: MagicMock,
) -> None:
    conv_chain = _chain(execute_data={"customer_id": "cust-1"})
    in_progress = {
        **_BOOKING_ROW,
        "start_at": (datetime.now(UTC) - timedelta(minutes=15)).isoformat(),
        "end_at": (datetime.now(UTC) + timedelta(minutes=45)).isoformat(),
        "customer_id": "cust-1",
    }
    book_chain = _chain(execute_data=[in_progress])

    def table(name: str) -> MagicMock:
        mocked = MagicMock()
        mocked.select.return_value = (
            conv_chain if name == "conversations" else book_chain
        )
        return mocked

    mock_client.return_value.table.side_effect = table

    result = run_list_conversation_bookings(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert len(result["bookings"]) == 1
    book_chain.gt.assert_called()
    assert book_chain.gt.call_args[0][0] == "end_at"


@patch("chatty_agent_common.scheduling.manage._get_client")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_fetch_booking_for_mutation_allows_customer_id_owner(
    _mock_org: object,
    mock_client: MagicMock,
) -> None:
    from chatty_agent_common.scheduling.manage import _fetch_booking_for_mutation

    conv_chain = _chain(execute_data={"customer_id": "cust-1"})
    book_chain = _chain(
        execute_data={
            **_BOOKING_ROW,
            "conversation_id": None,
            "customer_id": "cust-1",
        }
    )

    def table(name: str) -> MagicMock:
        mocked = MagicMock()
        mocked.select.return_value = (
            conv_chain if name == "conversations" else book_chain
        )
        return mocked

    mock_client.return_value.table.side_effect = table

    row = _fetch_booking_for_mutation("org-1", _CONV_ID, _BOOKING_ID)
    assert row is not None
    assert row["id"] == _BOOKING_ID
    book_chain.eq.assert_any_call("organization_id", "org-1")
    book_chain.eq.assert_any_call("id", _BOOKING_ID)


@patch("chatty_agent_common.scheduling.manage._get_client")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_fetch_booking_for_mutation_rejects_other_customer(
    _mock_org: object,
    mock_client: MagicMock,
) -> None:
    from chatty_agent_common.scheduling.manage import _fetch_booking_for_mutation

    conv_chain = _chain(execute_data={"customer_id": "cust-1"})
    book_chain = _chain(
        execute_data={
            **_BOOKING_ROW,
            "conversation_id": "other-conv",
            "customer_id": "cust-other",
        }
    )

    def table(name: str) -> MagicMock:
        mocked = MagicMock()
        mocked.select.return_value = (
            conv_chain if name == "conversations" else book_chain
        )
        return mocked

    mock_client.return_value.table.side_effect = table

    assert _fetch_booking_for_mutation("org-1", _CONV_ID, _BOOKING_ID) is None


@patch("chatty_agent_common.scheduling.manage._sync_booking_reminders")
@patch("chatty_agent_common.scheduling.manage._update_booking_status")
@patch("chatty_agent_common.scheduling.manage._fetch_booking_for_mutation")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_cancel_appointment_success(
    _mock_org: object,
    mock_fetch: MagicMock,
    mock_update: MagicMock,
    mock_sync: MagicMock,
) -> None:
    cancelled_row = {**_BOOKING_ROW, "status": "cancelled"}
    mock_fetch.return_value = _BOOKING_ROW
    mock_update.return_value = cancelled_row

    result = run_cancel_appointment(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        booking_id=_BOOKING_ID,
        timezone="America/La_Paz",
    )
    assert result["status"] == "cancelled"
    assert result["booking"]["booking_id"] == _BOOKING_ID
    mock_update.assert_called_once_with("org-1", _CONV_ID, _BOOKING_ID, "cancelled")
    mock_sync.assert_called_once_with("org-1", _BOOKING_ID)


@patch("chatty_agent_common.scheduling.manage._fetch_booking_for_mutation")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_cancel_appointment_not_found(
    _mock_org: object,
    mock_fetch: MagicMock,
) -> None:
    mock_fetch.return_value = None
    result = run_cancel_appointment(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        booking_id=_BOOKING_ID,
    )
    assert result["status"] == "error"
    assert "no pertenece" in result["message"].casefold()


@patch("chatty_agent_common.scheduling.manage._fetch_booking_for_mutation")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_cancel_appointment_past(
    _mock_org: object,
    mock_fetch: MagicMock,
) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    mock_fetch.return_value = {
        **_BOOKING_ROW,
        "start_at": past.isoformat(),
        "end_at": (past + timedelta(minutes=60)).isoformat(),
    }
    result = run_cancel_appointment(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        booking_id=_BOOKING_ID,
    )
    assert result["status"] == "error"
    assert "pasada" in result["message"].casefold()


@patch("chatty_agent_common.scheduling.manage._sync_booking_reminders")
@patch("chatty_agent_common.scheduling.manage._update_booking_times")
@patch("chatty_agent_common.scheduling.manage.list_schedules")
@patch("chatty_agent_common.scheduling.manage._fetch_booking_for_mutation")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_reschedule_appointment_success(
    _mock_org: object,
    mock_fetch: MagicMock,
    mock_schedules: MagicMock,
    mock_update: MagicMock,
    mock_sync: MagicMock,
) -> None:
    new_start = _FUTURE_START + timedelta(days=1)
    slot_id = f"sucre|{new_start.astimezone(UTC).isoformat().replace('+00:00', 'Z')}"
    updated_row = {
        **_BOOKING_ROW,
        "start_at": new_start.isoformat(),
        "end_at": (new_start + timedelta(minutes=60)).isoformat(),
    }
    mock_fetch.return_value = _BOOKING_ROW
    mock_schedules.return_value = _SCHEDULES
    mock_update.return_value = updated_row

    result = run_reschedule_appointment(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        booking_id=_BOOKING_ID,
        slot_id=slot_id,
        timezone="America/La_Paz",
    )
    assert result["status"] == "rescheduled"
    assert result["booking"]["booking_id"] == _BOOKING_ID
    mock_update.assert_called_once()
    mock_sync.assert_called_once_with("org-1", _BOOKING_ID)


@patch("chatty_agent_common.scheduling.manage._update_booking_times")
@patch("chatty_agent_common.scheduling.manage.list_schedules")
@patch("chatty_agent_common.scheduling.manage._fetch_booking_for_mutation")
@patch(
    "chatty_agent_common.scheduling.manage.get_organization_slug",
    return_value="org-1",
)
def test_reschedule_overlap_message(
    _mock_org: object,
    mock_fetch: MagicMock,
    mock_schedules: MagicMock,
    mock_update: MagicMock,
) -> None:
    new_start = _FUTURE_START + timedelta(days=1)
    slot_id = f"sucre|{new_start.astimezone(UTC).isoformat().replace('+00:00', 'Z')}"
    mock_fetch.return_value = _BOOKING_ROW
    mock_schedules.return_value = _SCHEDULES
    mock_update.side_effect = RuntimeError("That slot is no longer available.")

    result = run_reschedule_appointment(
        organization_slug=_ORG_SLUG,
        conversation_id=_CONV_ID,
        booking_id=_BOOKING_ID,
        slot_id=slot_id,
    )
    assert result["status"] == "error"
    assert "disponible" in result["message"].casefold()


def test_update_booking_times_resets_reminder_delivery_state() -> None:
    from chatty_agent_common.scheduling import manage as manage_module

    client = MagicMock()
    table = MagicMock()
    client.table.return_value = table
    table.update.return_value = table
    for method in ("eq", "select"):
        getattr(table, method).return_value = table
    table.execute.return_value = MagicMock(data={**_BOOKING_ROW})

    with patch.object(manage_module, "_get_client", return_value=client):
        manage_module._update_booking_times(
            "org-1",
            _CONV_ID,
            _BOOKING_ID,
            schedule_id="sched-1",
            start_at=_FUTURE_START,
            end_at=_FUTURE_END,
        )

    table.update.assert_called_once_with(
        {
            "schedule_id": "sched-1",
            "start_at": _FUTURE_START.astimezone(UTC).isoformat(),
            "end_at": _FUTURE_END.astimezone(UTC).isoformat(),
            "reminder_first_status": "pending",
            "reminder_second_status": "pending",
            "reminder_first_sent_at": None,
            "reminder_second_sent_at": None,
            "reminder_first_claimed_at": None,
            "reminder_second_claimed_at": None,
        }
    )


def test_update_booking_times_maps_exclusion_violation() -> None:
    from chatty_agent_common.scheduling import manage as manage_module

    client = MagicMock()
    table = MagicMock()
    client.table.return_value = table
    table.update.return_value = table
    for method in ("eq", "select"):
        getattr(table, method).return_value = table
    table.execute.side_effect = APIError({"message": "overlap", "code": "23P01"})

    with patch.object(manage_module, "_get_client", return_value=client):
        with pytest.raises(RuntimeError, match="no longer available"):
            manage_module._update_booking_times(
                "org-1",
                _CONV_ID,
                _BOOKING_ID,
                schedule_id="sched-1",
                start_at=_FUTURE_START,
                end_at=_FUTURE_END,
            )


@patch("chatty_agent_common.scheduling.manage.api_request")
def test_sync_booking_reminders_posts(mock_api: MagicMock) -> None:
    _sync_booking_reminders("org-1", _BOOKING_ID)
    mock_api.assert_called_once_with(
        "POST",
        f"/scheduling/bookings/{_BOOKING_ID}/reminders/sync",
        body={"organizationId": "org-1"},
    )


@patch(
    "chatty_agent_common.scheduling.manage.api_request",
    side_effect=RuntimeError("CHATTY_API_URL missing"),
)
def test_sync_booking_reminders_fail_open(_mock_api: MagicMock) -> None:
    _sync_booking_reminders("org-1", _BOOKING_ID)
