"""Unit tests for run_check_availability."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from chatty_agent_common.scheduling import (
    run_check_availability,
    run_list_available_days,
    run_list_available_hours,
)

_TZ = ZoneInfo("America/La_Paz")


def _next_weekday_local(hour: int = 9, minute: int = 0) -> datetime:
    day = datetime.now(_TZ).date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=_TZ)


def _next_slot_iso() -> str:
    local = _next_weekday_local()
    return local.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")


def test_empty_organization_slug() -> None:
    result = run_check_availability(
        organization_slug="",
        schedule_slug="sucre",
    )
    assert result["status"] == "error"
    assert result["slots"] == []
    assert result["available_days"] == []


def test_empty_schedule_slug() -> None:
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="",
    )
    assert result["status"] == "error"


@patch(
    "chatty_agent_common.scheduling.availability.api_request",
    return_value={"days": []},
)
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_empty_slots_ok(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="sucre",
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert result["slots"] == []
    assert result["days"] == []
    mock_api.assert_called_once()
    query = mock_api.call_args.kwargs["query"]
    assert query["scheduleSlug"] == "sucre"
    assert query["groupBy"] == "day"
    assert query["maxDays"] == "5"
    assert query["maxSlotsPerDay"] == "6"
    assert "preferredDate" not in query


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_returns_grouped_days(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    local_a = _next_weekday_local(9, 0)
    local_b = local_a + timedelta(days=1)
    while local_b.weekday() >= 5:
        local_b += timedelta(days=1)
    start_a = local_a.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
    start_b = local_b.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
    mock_api.return_value = {
        "days": [
            {
                "date": local_a.date().isoformat(),
                "slots": [
                    {"id": f"sucre|{start_a}", "start": start_a, "end": start_a},
                ],
            },
            {
                "date": local_b.date().isoformat(),
                "slots": [
                    {"id": f"sucre|{start_b}", "start": start_b, "end": start_b},
                ],
            },
        ],
    }
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="sucre",
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert len(result["available_days"]) == 2
    assert len(result["days"]) == 2
    assert len(result["slots"]) == 2
    assert result["slots"][0]["slot_id"].startswith("sucre|")
    assert "weekday" in result["available_days"][0]
    assert result["message"].startswith("2 día(s) con cupos:")


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_preferred_date_omits_max_days(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    start = _next_slot_iso()
    day = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(_TZ)
    mock_api.return_value = {
        "days": [
            {
                "date": day.date().isoformat(),
                "slots": [{"id": f"sucre|{start}", "start": start, "end": start}],
            }
        ],
    }
    preferred = day.date().isoformat()
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="sucre",
        preferred_date=preferred,
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    query = mock_api.call_args.kwargs["query"]
    assert query["preferredDate"] == preferred
    assert query["maxSlotsPerDay"] == "24"
    assert "maxDays" not in query
    assert len(result["days"]) == 1
    assert result["message"].startswith("Cupos para ")
    assert preferred in result["message"]


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_legacy_flat_list_still_works(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    start = _next_slot_iso()
    mock_api.return_value = [
        {"id": f"sucre|{start}", "start": start, "end": start},
    ]
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="sucre",
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert len(result["slots"]) == 1
    assert len(result["available_days"]) == 1


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_skips_malformed_slots_in_grouped_days(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    start = _next_slot_iso()
    day = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(_TZ)
    mock_api.return_value = {
        "days": [
            {
                "date": day.date().isoformat(),
                "slots": [
                    {"id": "sucre|bad", "start": "not-an-iso-timestamp"},
                    {"id": f"sucre|{start}", "start": start, "end": start},
                ],
            }
        ],
    }
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="sucre",
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert len(result["slots"]) == 1
    assert result["slots"][0]["slot_id"] == f"sucre|{start}"


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_skips_malformed_slots_in_flat_list(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    start = _next_slot_iso()
    mock_api.return_value = [
        {"id": "sucre|bad", "start": "not-an-iso-timestamp"},
        {"id": f"sucre|{start}", "start": start, "end": start},
    ]
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="sucre",
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert len(result["slots"]) == 1
    assert result["slots"][0]["slot_id"] == f"sucre|{start}"


@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_past_date_rejected(_mock_org: MagicMock) -> None:
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="sucre",
        preferred_date="2020-01-01",
        timezone="America/La_Paz",
    )
    assert result["status"] == "error"
    assert "past" in result["message"].casefold()


def test_invalid_date_format() -> None:
    result = run_check_availability(
        organization_slug="be-unique",
        schedule_slug="sucre",
        preferred_date="not-a-date",
    )
    assert result["status"] == "error"
    assert "Unrecognized date" in result["message"]


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_list_available_days_strips_slots(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    start = _next_slot_iso()
    day = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(_TZ)
    mock_api.return_value = {
        "days": [
            {
                "date": day.date().isoformat(),
                "slots": [{"id": f"sucre|{start}", "start": start, "end": start}],
            }
        ],
    }
    result = run_list_available_days(
        organization_slug="be-unique",
        schedule_slug="sucre",
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert result["slots"] == []
    assert result["days"] == []
    assert len(result["available_days"]) == 1
    assert "preferredDate" not in mock_api.call_args.kwargs["query"]
    assert mock_api.call_args.kwargs["query"]["maxDays"] == "5"


def test_list_available_hours_requires_date() -> None:
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date="",
        timezone="America/La_Paz",
    )
    assert result["status"] == "error"
    assert "required" in result["message"].casefold()


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_list_available_hours_sends_preferred_date(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    start = _next_slot_iso()
    day = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(_TZ)
    preferred = day.date().isoformat()
    mock_api.return_value = {
        "days": [
            {
                "date": preferred,
                "slots": [{"id": f"sucre|{start}", "start": start, "end": start}],
            }
        ],
    }
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date=preferred,
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert len(result["slots"]) == 1
    query = mock_api.call_args.kwargs["query"]
    assert query["preferredDate"] == preferred
    assert "maxDays" not in query
    assert result["message"].startswith("Cupos para ")
    assert result["slots"][0]["time"] == "9:00 AM"
    assert result["slots"][0]["period"] == "morning"
    assert result["needs_period_filter"] is False


def _slots_for_day(
    day: datetime,
    hours: list[tuple[int, int]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for hour, minute in hours:
        local = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        start = local.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
        out.append({"id": f"sucre|{start}", "start": start, "end": start})
    return out


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_slot_time_12h_and_period_classification(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    day = _next_weekday_local(9, 0)
    preferred = day.date().isoformat()
    raw_slots = _slots_for_day(
        day,
        [(9, 0), (12, 0), (15, 30), (18, 0)],
    )
    mock_api.return_value = {"days": [{"date": preferred, "slots": raw_slots}]}
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date=preferred,
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    times = {s["time"] for s in result["slots"]}
    assert "9:00 AM" in times
    assert "12:00 PM" in times
    assert "3:30 PM" in times
    assert "6:00 PM" in times
    by_time = {s["time"]: s["period"] for s in result["slots"]}
    assert by_time["9:00 AM"] == "morning"
    assert by_time["12:00 PM"] == "afternoon"
    assert by_time["3:30 PM"] == "afternoon"
    assert by_time["6:00 PM"] == "evening"
    assert result["period_counts"] == {
        "morning": 1,
        "afternoon": 2,
        "evening": 1,
    }


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_needs_period_filter_when_more_than_10_slots(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    day = _next_weekday_local(8, 0)
    preferred = day.date().isoformat()
    hours = [(8 + i, 0) for i in range(12)]  # 8-19 -> 12 slots
    mock_api.return_value = {
        "days": [{"date": preferred, "slots": _slots_for_day(day, hours)}],
    }
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date=preferred,
        timezone="America/La_Paz",
    )
    assert result["status"] == "ok"
    assert result["needs_period_filter"] is True
    assert result["slots"] == []
    assert result["slot_count"] == 12
    assert result["period_counts"]["morning"] > 0
    assert result["period_counts"]["afternoon"] > 0
    assert all(d["slots"] == [] for d in result["days"])


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_period_filter_returns_matching_slots(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    day = _next_weekday_local(8, 0)
    preferred = day.date().isoformat()
    hours = [(8 + i, 0) for i in range(12)]
    mock_api.return_value = {
        "days": [{"date": preferred, "slots": _slots_for_day(day, hours)}],
    }
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date=preferred,
        timezone="America/La_Paz",
        period="afternoon",
    )
    assert result["status"] == "ok"
    assert result["needs_period_filter"] is False
    assert result["slots"]
    assert all(s["period"] == "afternoon" for s in result["slots"])
    assert result["slot_count"] == 12


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_period_filter_truncates_over_10(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    day = _next_weekday_local(8, 0)
    preferred = day.date().isoformat()
    # 11 morning slots only (hour < 12)
    hours = [(i, 0) for i in range(1, 12)]
    mock_api.return_value = {
        "days": [{"date": preferred, "slots": _slots_for_day(day, hours)}],
    }
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date=preferred,
        timezone="America/La_Paz",
        period="morning",
    )
    assert result["status"] == "ok"
    assert result["truncated"] is True
    assert len(result["slots"]) == 10
    assert "mostrando 10" in result["message"].casefold()


@patch("chatty_agent_common.scheduling.availability.api_request")
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_invalid_period_returns_error(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    day = _next_weekday_local(9, 0)
    preferred = day.date().isoformat()
    mock_api.return_value = {
        "days": [
            {
                "date": preferred,
                "slots": _slots_for_day(day, [(9, 0)]),
            }
        ],
    }
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date=preferred,
        timezone="America/La_Paz",
        period="brunch",
    )
    assert result["status"] == "error"
    assert result.get("error_code") == "invalid_period"
    assert "period" in result["message"].casefold()


def test_hours_beyond_horizon_without_api() -> None:
    today = datetime.now(_TZ).date()
    beyond = (today + timedelta(days=30)).isoformat()
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date=beyond,
        timezone="America/La_Paz",
        max_days_ahead=7,
    )
    assert result["status"] == "ok"
    assert result["availability_kind"] == "beyond_horizon"
    assert result["date"] == beyond
    assert result["slots"] == []
    assert result["horizon_end"] is not None


@patch(
    "chatty_agent_common.scheduling.availability.api_request",
    return_value={"days": []},
)
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_hours_empty_day_inside_horizon(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    day = _next_weekday_local(9, 0)
    preferred = day.date().isoformat()
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date=preferred,
        timezone="America/La_Paz",
        max_days_ahead=14,
    )
    assert result["status"] == "ok"
    assert result["availability_kind"] == "empty_day"
    assert result["date"] == preferred
    mock_api.assert_called_once()


@patch(
    "chatty_agent_common.scheduling.availability.api_request",
    return_value={"days": []},
)
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_days_from_date_sends_tz_start_iso(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    anchor = (datetime.now(_TZ).date() + timedelta(days=3)).isoformat()
    run_list_available_days(
        organization_slug="be-unique",
        schedule_slug="sucre",
        from_date=anchor,
        timezone="America/La_Paz",
    )
    query = mock_api.call_args.kwargs["query"]
    assert "from" in query
    assert query["from"].startswith(anchor)
    assert "T" in query["from"]
    assert "preferredDate" not in query


@patch(
    "chatty_agent_common.scheduling.availability.api_request",
    return_value={"days": []},
)
@patch(
    "chatty_agent_common.scheduling.availability.get_organization_slug",
    return_value="org-1",
)
def test_days_to_date_sends_exclusive_next_day(
    _mock_org: MagicMock,
    mock_api: MagicMock,
) -> None:
    to_day = (datetime.now(_TZ).date() + timedelta(days=10)).isoformat()
    expected_next = (date.fromisoformat(to_day) + timedelta(days=1)).isoformat()
    run_list_available_days(
        organization_slug="be-unique",
        schedule_slug="sucre",
        to_date=to_day,
        timezone="America/La_Paz",
    )
    query = mock_api.call_args.kwargs["query"]
    assert query["to"].startswith(expected_next)


def test_hours_past_returns_error_code() -> None:
    result = run_list_available_hours(
        organization_slug="be-unique",
        schedule_slug="sucre",
        date="2020-01-01",
        timezone="America/La_Paz",
        max_days_ahead=7,
    )
    assert result["status"] == "error"
    assert result.get("error_code") == "past"
    assert "availability_kind" not in result
