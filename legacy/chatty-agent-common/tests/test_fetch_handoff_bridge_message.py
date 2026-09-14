"""Tests for CRM handoff_bridge_message lookup + resolve order."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from chatty_agent_common.handoff import resolve_handoff_bridge_message
from chatty_agent_common.providers.supabase import fetch_handoff_bridge_message

_DEFAULT = "fallback bridge"


def _mock_client_with_rows(rows: list[dict] | None) -> MagicMock:
    client = MagicMock()
    query = MagicMock()
    client.table.return_value = query
    query.select.return_value = query
    query.eq.return_value = query
    query.limit.return_value = query
    result = MagicMock()
    result.data = rows
    query.execute.return_value = result
    return client


@patch("chatty_agent_common.providers.supabase.get_supabase_client")
def test_fetch_returns_trimmed_message(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_client_with_rows(
        [
            {
                "inboxes": {
                    "ai_agents": {
                        "handoff_bridge_message": "  Hola Laura  ",
                    }
                }
            }
        ]
    )
    assert fetch_handoff_bridge_message("conv-1") == "Hola Laura"


@patch("chatty_agent_common.providers.supabase.get_supabase_client")
def test_fetch_returns_none_when_blank(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_client_with_rows(
        [{"inboxes": {"ai_agents": {"handoff_bridge_message": "   "}}}]
    )
    assert fetch_handoff_bridge_message("conv-1") is None


@patch("chatty_agent_common.providers.supabase.get_supabase_client")
def test_fetch_returns_none_when_conversation_missing(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_client_with_rows([])
    assert fetch_handoff_bridge_message("conv-missing") is None


def test_fetch_returns_none_for_empty_conversation_id() -> None:
    assert fetch_handoff_bridge_message("") is None
    assert fetch_handoff_bridge_message("   ") is None


@patch(
    "chatty_agent_common.handoff.fetch_handoff_bridge_message", return_value="DB msg"
)
def test_resolve_prefers_db_over_env(_mock_fetch: MagicMock) -> None:
    with patch.dict(os.environ, {"HANDOFF_BRIDGE_MESSAGE": "env msg"}, clear=False):
        assert resolve_handoff_bridge_message("conv-1", default=_DEFAULT) == "DB msg"


@patch("chatty_agent_common.handoff.fetch_handoff_bridge_message", return_value=None)
def test_resolve_uses_env_when_db_empty(_mock_fetch: MagicMock) -> None:
    with patch.dict(os.environ, {"HANDOFF_BRIDGE_MESSAGE": "env msg"}, clear=False):
        assert resolve_handoff_bridge_message("conv-1", default=_DEFAULT) == "env msg"


@patch("chatty_agent_common.handoff.fetch_handoff_bridge_message", return_value=None)
def test_resolve_uses_default_when_db_and_env_empty(_mock_fetch: MagicMock) -> None:
    with patch.dict(os.environ, {"HANDOFF_BRIDGE_MESSAGE": ""}, clear=False):
        assert resolve_handoff_bridge_message("conv-1", default=_DEFAULT) == _DEFAULT
