"""Tests for ADK dev-mode graceful handoff when conversation row is missing."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from chatty_agent_common.handoff import execute_conversation_handoff

_SOURCE = "test_workflow"


@patch("chatty_agent_common.handoff.update_conversation_status")
def test_dev_mode_skips_update_when_conversation_missing(
    mock_update: MagicMock,
) -> None:
    mock_update.side_effect = RuntimeError(
        "No conversation updated for id=conv-missing (missing row or invalid id)"
    )

    with patch.dict(os.environ, {"ADK_DEV_MODE": "true"}, clear=False):
        result = execute_conversation_handoff(
            "conv-missing",
            85,
            "Lead calificado para prueba.",
            source=_SOURCE,
        )

    assert result["status"] == "success"
    assert result["conversation_status"] == "WAITING_HUMAN"
    assert result["conversation_id"] == "conv-missing"
    assert result["score"] == 85


@patch("chatty_agent_common.handoff.update_conversation_status")
def test_dev_mode_reraises_non_missing_runtime_error(
    mock_update: MagicMock,
) -> None:
    mock_update.side_effect = RuntimeError(
        "Cannot connect to Supabase (check SUPABASE_URL). If you run the agent on your "
        "machine, use the local API URL from `supabase status` (typically "
        "http://127.0.0.1:54321). Hostnames like api.supabase.internal only resolve "
        "inside Docker/the same private network."
    )

    with patch.dict(os.environ, {"ADK_DEV_MODE": "true"}, clear=False):
        with pytest.raises(RuntimeError, match="Cannot connect to Supabase"):
            execute_conversation_handoff(
                "conv-1",
                85,
                "Lead calificado para prueba.",
                source=_SOURCE,
            )


@patch("chatty_agent_common.handoff.update_conversation_status")
def test_handoff_sends_metadata_patch_only(
    mock_update: MagicMock,
) -> None:
    mock_update.return_value = {
        "id": "conv-1",
        "status": "WAITING_HUMAN",
        "qualification_score": 85,
        "handoff_reason": "Lead calificado para prueba.",
    }

    execute_conversation_handoff(
        "conv-1",
        85,
        "Lead calificado para prueba.",
        source=_SOURCE,
    )

    patch = mock_update.call_args.kwargs["metadata_patch"]
    assert set(patch.keys()) == {"handoff"}
    assert patch["handoff"]["score"] == 85
    assert patch["handoff"]["source"] == _SOURCE


@patch("chatty_agent_common.handoff.update_conversation_status")
def test_handoff_persists_qualification_columns(
    mock_update: MagicMock,
) -> None:
    mock_update.return_value = {
        "id": "conv-1",
        "status": "HUMAN_ACTIVE",
        "qualification_score": 85,
        "handoff_reason": "Lead calificado para prueba.",
    }

    result = execute_conversation_handoff(
        "conv-1",
        85,
        "Lead calificado para prueba.",
        source=_SOURCE,
    )

    mock_update.assert_called_once()
    kwargs = mock_update.call_args.kwargs
    assert kwargs["conversation_id"] == "conv-1"
    assert kwargs["status"] == "WAITING_HUMAN"
    assert kwargs["stage"] == "handed_off"
    assert kwargs["qualification_score"] == 85
    assert kwargs["handoff_reason"] == "Lead calificado para prueba."
    assert kwargs["metadata_patch"]["handoff"]["score"] == 85
    assert (
        kwargs["metadata_patch"]["handoff"]["reason"] == "Lead calificado para prueba."
    )
    assert kwargs["metadata_patch"]["handoff"]["source"] == _SOURCE
    assert result["score"] == 85


@patch("chatty_agent_common.handoff.update_conversation_status")
def test_production_mode_raises_when_conversation_missing(
    mock_update: MagicMock,
) -> None:
    mock_update.side_effect = RuntimeError(
        "No conversation updated for id=conv-missing (missing row or invalid id)"
    )

    with patch.dict(os.environ, {"ADK_DEV_MODE": "false"}, clear=False):
        with pytest.raises(RuntimeError, match="No conversation updated"):
            execute_conversation_handoff(
                "conv-missing",
                85,
                "Lead calificado para prueba.",
                source=_SOURCE,
            )


def test_empty_source_rejected() -> None:
    with pytest.raises(ValueError, match="source cannot be empty"):
        execute_conversation_handoff("conv-1", 10, "reason", source="")
