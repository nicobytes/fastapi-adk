"""Unit tests for run_book_appointment."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from chatty_agent_common.scheduling import run_book_appointment

_TZ = ZoneInfo("America/La_Paz")


def _next_slot_iso() -> str:
    day = datetime.now(_TZ).date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    local = datetime(day.year, day.month, day.day, 9, 0, tzinfo=_TZ)
    return local.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")


def test_missing_slot_id() -> None:
    result = run_book_appointment(
        organization_slug="be-unique",
        schedule_slug="sucre",
        service_name="Depilación",
        slot_id="",
    )
    assert result["status"] == "error"
    assert "slot_id" in result["message"]


@patch("chatty_agent_common.scheduling.booking.api_request")
@patch(
    "chatty_agent_common.scheduling.booking.get_organization_slug",
    return_value="org-1",
)
def test_book_success(
    _mock_org: object,
    mock_api: object,
) -> None:
    start = _next_slot_iso()
    slot_id = f"sucre|{start}"
    mock_api.return_value = {
        "id": "bk-123",
        "startAt": start,
        "status": "confirmed",
    }
    result = run_book_appointment(
        organization_slug="be-unique",
        schedule_slug="sucre",
        service_name="Depilación",
        slot_id=slot_id,
        metadata={"customer_name": "María"},
        timezone="America/La_Paz",
    )
    assert result["status"] == "booked"
    assert result["booking"]["booking_id"] == "bk-123"
    assert result["booking"]["schedule_slug"] == "sucre"
    mock_api.assert_called_once()
    assert mock_api.call_args.args[0] == "POST"
    assert mock_api.call_args.args[1] == "/scheduling/bookings"
    assert mock_api.call_args.kwargs["body"]["slotId"] == slot_id
    assert "conversationId" not in mock_api.call_args.kwargs["body"]


@patch("chatty_agent_common.scheduling.booking.api_request")
@patch(
    "chatty_agent_common.scheduling.booking.get_organization_slug",
    return_value="org-1",
)
def test_book_forwards_conversation_id(
    _mock_org: object,
    mock_api: object,
) -> None:
    start = _next_slot_iso()
    slot_id = f"sucre|{start}"
    mock_api.return_value = {
        "id": "bk-456",
        "startAt": start,
        "status": "confirmed",
    }
    result = run_book_appointment(
        organization_slug="be-unique",
        schedule_slug="sucre",
        service_name="Depilación",
        slot_id=slot_id,
        conversation_id="  conv-abc  ",
        timezone="America/La_Paz",
    )
    assert result["status"] == "booked"
    assert mock_api.call_args.kwargs["body"]["conversationId"] == "conv-abc"


@patch(
    "chatty_agent_common.scheduling.booking.api_request",
    side_effect=RuntimeError("API 409: Conflict"),
)
@patch(
    "chatty_agent_common.scheduling.booking.get_organization_slug",
    return_value="org-1",
)
def test_conflict_message(
    _mock_org: object,
    _mock_api: object,
) -> None:
    result = run_book_appointment(
        organization_slug="be-unique",
        schedule_slug="sucre",
        service_name="Depilación",
        slot_id=f"sucre|{_next_slot_iso()}",
    )
    assert result["status"] == "error"
    assert "no longer available" in result["message"].casefold()
