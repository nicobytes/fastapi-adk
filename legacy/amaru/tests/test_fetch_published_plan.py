"""fetch_published_plan: tenant-scoped page by canonical URL."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.subagents.customer.tools.fetch_published_plan import (
    canonical_page_url,
    fetch_published_plan,
)


def test_canonical_page_url_https_host_slash_query_hash() -> None:
    assert (
        canonical_page_url("http://Example.TEST/tours/foo/")
        == "https://example.test/tours/foo"
    )
    assert (
        canonical_page_url("https://example.test/tours/foo?x=1#/bar/")
        == "https://example.test/tours/foo?x=1#/bar"
    )
    assert canonical_page_url("  ") == ""


class _FakeQuery:
    def __init__(self, data: list[dict] | None) -> None:
        self.data = data if data is not None else []
        self.eqs: list[tuple[str, object]] = []
        self.in_filters: list[tuple[str, object]] = []

    def select(self, *_args: object, **_kwargs: object) -> _FakeQuery:
        return self

    def eq(self, column: str, value: object) -> _FakeQuery:
        self.eqs.append((column, value))
        return self

    def in_(self, column: str, value: object) -> _FakeQuery:
        self.in_filters.append((column, value))
        return self

    def order(self, *_args: object, **_kwargs: object) -> _FakeQuery:
        return self

    def limit(self, *_args: object, **_kwargs: object) -> _FakeQuery:
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self.data)


def test_fetch_returns_usable_chunked_row() -> None:
    query = _FakeQuery(
        [
            {
                "title": "Tour A",
                "source_url": "https://example.test/a",
                "content": "## Incluye\n\ntransporte",
                "is_active": True,
                "status": "chunked",
                "knowledge_base": {"is_active": True},
            }
        ]
    )
    client = MagicMock()
    client.table.return_value = query

    with (
        patch(
            "app.subagents.customer.tools.fetch_published_plan.get_organization_slug",
            return_value="org-amaru",
        ),
        patch(
            "app.subagents.customer.tools.fetch_published_plan.get_supabase_client",
            return_value=client,
        ),
    ):
        page = fetch_published_plan("HTTP://Example.TEST/a/")

    assert page == {
        "title": "Tour A",
        "source_url": "https://example.test/a",
        "content": "## Incluye\n\ntransporte",
    }
    client.table.assert_called_once_with("knowledge_source")
    assert ("organization_id", "org-amaru") in query.eqs
    assert ("source_url", "https://example.test/a") in query.eqs
    assert ("is_active", True) in query.eqs


def test_fetch_empty_or_inactive_returns_none() -> None:
    empty = _FakeQuery(
        [
            {
                "title": "Tour A",
                "source_url": "https://example.test/a",
                "content": "   ",
                "is_active": True,
                "status": "chunked",
                "knowledge_base": {"is_active": True},
            }
        ]
    )
    client = MagicMock()
    client.table.return_value = empty

    with (
        patch(
            "app.subagents.customer.tools.fetch_published_plan.get_organization_slug",
            return_value="org-amaru",
        ),
        patch(
            "app.subagents.customer.tools.fetch_published_plan.get_supabase_client",
            return_value=client,
        ),
    ):
        assert fetch_published_plan("https://example.test/a") is None

    none_rows = _FakeQuery([])
    client.table.return_value = none_rows
    with (
        patch(
            "app.subagents.customer.tools.fetch_published_plan.get_organization_slug",
            return_value="org-amaru",
        ),
        patch(
            "app.subagents.customer.tools.fetch_published_plan.get_supabase_client",
            return_value=client,
        ),
    ):
        assert fetch_published_plan("https://example.test/missing") is None
