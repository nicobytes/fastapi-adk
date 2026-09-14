"""Unit tests for scheduling catalog list/resolve helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chatty_agent_common.scheduling.catalog import (
    list_schedules,
    resolve_schedule,
)

_SCHEDULES = [
    {
        "id": "s1",
        "name": "Sucre",
        "slug": "sucre",
        "timezone": "America/La_Paz",
        "is_default": True,
        "is_active": True,
    },
    {
        "id": "s2",
        "name": "Cochabamba",
        "slug": "cochabamba",
        "timezone": "America/La_Paz",
        "is_default": False,
        "is_active": True,
    },
]


def test_resolve_schedule_by_name() -> None:
    row, err = resolve_schedule(_SCHEDULES, "sucre")
    assert err is None
    assert row is not None
    assert row["slug"] == "sucre"


def test_resolve_schedule_by_display_name_casefold() -> None:
    row, err = resolve_schedule(_SCHEDULES, "COCHABAMBA")
    assert err is None
    assert row is not None
    assert row["name"] == "Cochabamba"


def test_resolve_schedule_accepts_sede_prefix() -> None:
    row, err = resolve_schedule(_SCHEDULES, "sede_sucre")
    assert err is None
    assert row is not None
    assert row["slug"] == "sucre"


def test_resolve_schedule_unknown_multi_errors() -> None:
    row, err = resolve_schedule(_SCHEDULES, "La Paz")
    assert row is None
    assert err is not None
    assert "Sucre" in err
    assert "Cochabamba" in err


def test_resolve_schedule_empty_sede_multi_errors() -> None:
    row, err = resolve_schedule(_SCHEDULES, "  ")
    assert row is None
    assert err is not None
    assert "Falta" in err


def test_resolve_schedule_single_always_returns_that_row() -> None:
    schedules = [
        {
            "id": "s1",
            "name": "General",
            "slug": "general",
            "timezone": "America/La_Paz",
            "is_default": True,
            "is_active": True,
        }
    ]
    row, err = resolve_schedule(schedules, "Sucre")
    assert err is None
    assert row is not None
    assert row["slug"] == "general"

    row_empty, err_empty = resolve_schedule(schedules, "")
    assert err_empty is None
    assert row_empty is not None
    assert row_empty["slug"] == "general"


def test_resolve_schedule_no_schedules() -> None:
    row, err = resolve_schedule([], "Sucre")
    assert row is None
    assert err is not None
    assert "No hay horarios" in err


def test_list_schedules_empty_org() -> None:
    with pytest.raises(ValueError):
        list_schedules("  ")


@patch("chatty_agent_common.scheduling.catalog.get_supabase_client")
def test_list_schedules_maps_rows(mock_client: MagicMock) -> None:
    table = MagicMock()
    mock_client.return_value.table.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.order.return_value = table
    table.execute.return_value = MagicMock(
        data=[
            {
                "id": "s1",
                "name": "Sucre",
                "slug": "sucre",
                "timezone": "America/La_Paz",
                "duration_minutes": 60,
                "is_default": True,
                "is_active": True,
                "max_days_ahead": 14,
            }
        ]
    )

    rows = list_schedules("org-1")
    assert len(rows) == 1
    assert rows[0]["slug"] == "sucre"
    assert rows[0]["max_days_ahead"] == 14
    mock_client.return_value.table.assert_called_with("schedules")
