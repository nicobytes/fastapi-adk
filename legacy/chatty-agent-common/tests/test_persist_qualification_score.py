"""Tests for best-effort qualification snapshot persistence."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from chatty_agent_common.handoff import persist_conversation_qualification_snapshot

_CRITERIA = {
    "interest_level": "High",
    "budget_status": "Aligned",
    "purchase_urgency": "ShortTerm",
    "has_decision_authority": True,
    "explicit_human_request": False,
    "plan_and_date_confirmed": False,
}


@patch("chatty_agent_common.handoff.update_conversation_qualification_score")
def test_persist_qualification_snapshot_sends_patch_only(
    mock_update: MagicMock,
) -> None:
    persist_conversation_qualification_snapshot(
        "conv-1",
        90,
        _CRITERIA,
        True,
    )

    mock_update.assert_called_once()
    kwargs = mock_update.call_args.kwargs
    assert kwargs["conversation_id"] == "conv-1"
    assert kwargs["qualification_score"] == 90
    patch = kwargs["metadata_patch"]
    assert set(patch.keys()) == {"qualification"}
    qualification = patch["qualification"]
    assert qualification["interest_level"] == "High"
    assert qualification["score"] == 90
    assert qualification["qualifies"] is True
    assert "updated_at" in qualification


@patch("chatty_agent_common.handoff.update_conversation_qualification_score")
def test_persist_skips_missing_row_in_dev_mode(
    mock_update: MagicMock,
) -> None:
    mock_update.side_effect = RuntimeError(
        "No conversation updated for id=conv-missing (missing row or invalid id)"
    )

    with patch.dict(os.environ, {"ADK_DEV_MODE": "true"}, clear=False):
        persist_conversation_qualification_snapshot(
            "conv-missing",
            45,
            _CRITERIA,
            False,
        )

    mock_update.assert_called_once()
    kwargs = mock_update.call_args.kwargs
    assert kwargs["conversation_id"] == "conv-missing"
    assert kwargs["qualification_score"] == 45
    qualification = kwargs["metadata_patch"]["qualification"]
    assert qualification["interest_level"] == "High"
    assert qualification["score"] == 45
    assert qualification["qualifies"] is False
    assert "updated_at" in qualification


@patch("chatty_agent_common.handoff.logger")
@patch("chatty_agent_common.handoff.update_conversation_qualification_score")
def test_persist_logs_non_missing_runtime_error_in_dev_mode(
    mock_update: MagicMock,
    mock_logger: MagicMock,
) -> None:
    mock_update.side_effect = RuntimeError(
        "Cannot connect to Supabase (check SUPABASE_URL). If you run the agent on your "
        "machine, use the local API URL from `supabase status` (typically "
        "http://127.0.0.1:54321). Hostnames like api.supabase.internal only resolve "
        "inside Docker/the same private network."
    )

    with patch.dict(os.environ, {"ADK_DEV_MODE": "true"}, clear=False):
        persist_conversation_qualification_snapshot(
            "conv-1",
            45,
            _CRITERIA,
            False,
        )

    mock_update.assert_called_once()
    mock_logger.exception.assert_called_once()
    assert (
        "Failed to persist qualification snapshot"
        in mock_logger.exception.call_args.args[0]
    )


@patch("chatty_agent_common.handoff.update_conversation_qualification_score")
def test_persist_does_not_raise_on_production_failure(
    mock_update: MagicMock,
) -> None:
    mock_update.side_effect = RuntimeError(
        "No conversation updated for id=conv-missing (missing row or invalid id)"
    )

    with patch.dict(os.environ, {"ADK_DEV_MODE": "false"}, clear=False):
        persist_conversation_qualification_snapshot(
            "conv-missing",
            45,
            _CRITERIA,
            False,
        )

    mock_update.assert_called_once()
