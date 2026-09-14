"""Unit tests for shared knowledge search helper."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from chatty_agent_common.knowledge_search import run_knowledge_search


def test_empty_query_raises() -> None:
    with pytest.raises(ValueError, match="Query cannot be empty"):
        run_knowledge_search(
            organization_slug="amaru",
            query="  ",
            match_count=4,
        )


def test_empty_organization_slug_raises() -> None:
    with pytest.raises(ValueError, match="organization_slug cannot be empty"):
        run_knowledge_search(
            organization_slug="",
            query="planes",
            match_count=4,
        )


@patch("chatty_agent_common.knowledge_search.search_knowledge")
@patch(
    "chatty_agent_common.knowledge_search.get_organization_slug",
    return_value="org-1",
)
def test_happy_path_serializes_rows(
    _mock_org: object,
    mock_search: object,
) -> None:
    mock_search.return_value = [
        {"id": "a", "content": "hello", "metadata": {"k": 1}},
        {"id": "b", "content": "world", "metadata": None},
    ]

    result = run_knowledge_search(
        organization_slug="amaru",
        query="planes",
        match_count=4,
    )

    mock_search.assert_called_once()
    assert "Result 1\nContent: hello" in result["content"]
    assert "Result 2\nContent: world" in result["content"]
    assert result["artifact"] == [
        {"id": "a", "content": "hello", "metadata": {"k": 1}},
        {"id": "b", "content": "world", "metadata": {}},
    ]


@patch("chatty_agent_common.knowledge_search.search_knowledge")
@patch(
    "chatty_agent_common.knowledge_search.get_organization_slug",
    return_value="org-1",
)
def test_runtime_error_returns_empty_result(
    _mock_org: object,
    mock_search: object,
) -> None:
    mock_search.side_effect = RuntimeError("boom")

    result = run_knowledge_search(
        organization_slug="be-unique",
        query="laser",
        match_count=4,
    )

    assert result["artifact"] == []
    assert "No relevant results found" in result["content"]
