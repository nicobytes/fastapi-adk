"""Amaru search_context groups chunks by plan; artifact stays flat."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from unittest.mock import patch

from app.subagents.customer.tools.search_context import _ORG_SLUG, search_context

_EMPTY_RESULT = {
    "content": (
        "No relevant results found for this query in the organization's knowledge base."
    ),
    "artifact": [],
}

_DIGEST_KEYS = {"plan_count", "plans", "content", "active_plan", "artifact"}


class _Ctx:
    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = {} if state is None else state


def _chunk(
    *,
    chunk_id: str,
    content: str,
    source_url: str | None = None,
    record_title: str = "",
    heading: str = "",
    chunk_index: int | None = None,
) -> dict:
    metadata: dict[str, Any] = {}
    if source_url:
        metadata["source_url"] = source_url
    if record_title:
        metadata["record_title"] = record_title
    if heading:
        metadata["heading"] = heading
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index
    return {"id": chunk_id, "content": content, "metadata": metadata}


def _h2_count(content: str) -> int:
    return sum(1 for line in content.splitlines() if line.startswith("## "))


def test_search_context_uses_amaru_slug() -> None:
    with patch(
        "app.subagents.customer.tools.search_context.run_knowledge_search",
        return_value=_EMPTY_RESULT,
    ) as mock_search:
        result = search_context("planes")

    mock_search.assert_called_once_with(
        organization_slug="amaru",
        query="planes",
        match_count=10,
    )
    assert result == _EMPTY_RESULT
    assert _ORG_SLUG == "amaru"


def test_same_source_url_becomes_one_plan_block() -> None:
    artifact = [
        _chunk(
            chunk_id="a1",
            content="incluye transporte",
            source_url="https://example.test/a",
            record_title="Tour A",
            heading="Incluye",
        ),
        _chunk(
            chunk_id="a2",
            content="sale en marzo",
            source_url="https://example.test/a",
            record_title="Tour A",
            heading="Fechas",
        ),
    ]
    helper = {
        "content": "Result 1\nContent: incluye transporte\n\nResult 2\nContent: sale en marzo",
        "artifact": deepcopy(artifact),
    }

    with patch(
        "app.subagents.customer.tools.search_context.run_knowledge_search",
        return_value=helper,
    ):
        result = search_context("tour a")

    assert set(result.keys()) == _DIGEST_KEYS
    assert result["plan_count"] == 1
    assert result["plans"] == [
        {"title": "Tour A", "source_url": "https://example.test/a"}
    ]
    assert _h2_count(result["content"]) == 1
    assert "## Tour A" in result["content"]
    assert "url: https://example.test/a" in result["content"]
    assert "### Incluye" in result["content"]
    assert "incluye transporte" in result["content"]
    assert "### Fechas" in result["content"]
    assert "sale en marzo" in result["content"]
    assert result["active_plan"] is None
    assert len(result["artifact"]) == 2
    assert result["artifact"] == helper["artifact"]


def test_distinct_source_urls_become_two_plan_blocks() -> None:
    artifact = [
        _chunk(
            chunk_id="a",
            content="alpha",
            source_url="https://example.test/a",
            record_title="Tour A",
            heading="Resumen",
        ),
        _chunk(
            chunk_id="b",
            content="beta",
            source_url="https://example.test/b",
            record_title="Tour B",
            heading="Resumen",
        ),
    ]
    helper = {"content": "Result 1\nContent: alpha", "artifact": deepcopy(artifact)}

    with patch(
        "app.subagents.customer.tools.search_context.run_knowledge_search",
        return_value=helper,
    ):
        result = search_context("tours")

    assert result["plan_count"] == 2
    assert _h2_count(result["content"]) == 2
    assert result["content"].index("## Tour A") < result["content"].index("## Tour B")
    assert len(result["artifact"]) == 2
    assert result["artifact"] == helper["artifact"]


def test_inline_plan_field_becomes_title() -> None:
    artifact = [
        _chunk(
            chunk_id="a",
            content="**PLAN:** Foo Bar **CATEGORÍA:** Alta",
            source_url="https://example.test/foo-bar",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}

    with patch(
        "app.subagents.customer.tools.search_context.run_knowledge_search",
        return_value=helper,
    ):
        result = search_context("foo")

    assert "## Foo Bar" in result["content"]
    assert "Plan: **" not in result["content"]
    assert result["plans"][0]["title"] == "Foo Bar"


def test_chunk_index_orders_sections() -> None:
    artifact = [
        _chunk(
            chunk_id="late",
            content="despues",
            source_url="https://example.test/a",
            record_title="Tour A",
            chunk_index=2,
        ),
        _chunk(
            chunk_id="early",
            content="antes",
            source_url="https://example.test/a",
            record_title="Tour A",
            chunk_index=0,
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}

    with patch(
        "app.subagents.customer.tools.search_context.run_knowledge_search",
        return_value=helper,
    ):
        result = search_context("tour a")

    assert result["content"].index("antes") < result["content"].index("despues")
    assert result["artifact"][0]["id"] == "late"


def test_explore_clears_saved_plan_and_returns_all() -> None:
    artifact = [
        _chunk(
            chunk_id="a",
            content="alpha",
            source_url="https://example.test/a",
            record_title="Tour A",
        ),
        _chunk(
            chunk_id="b",
            content="beta",
            source_url="https://example.test/b",
            record_title="Tour B",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}
    state = {
        "active_plan_title": "Tour A",
        "active_plan_url": "https://example.test/a",
    }

    with patch(
        "app.subagents.customer.tools.search_context.run_knowledge_search",
        return_value=helper,
    ) as mock_search:
        result = search_context(
            "opciones",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="Tour A",
            explore=True,
        )

    mock_search.assert_called_once_with(
        organization_slug="amaru",
        query="opciones",
        match_count=10,
    )
    assert result["plan_count"] == 2
    assert "## Tour A" in result["content"]
    assert "## Tour B" in result["content"]
    assert result["active_plan"] is None
    assert state["active_plan_title"] == ""
    assert state["active_plan_url"] == ""
    assert len(result["artifact"]) == 2


def test_plan_focus_filters_content_and_sets_state() -> None:
    artifact = [
        _chunk(
            chunk_id="a",
            content="alpha",
            source_url="https://example.test/a",
            record_title="Tour A",
        ),
        _chunk(
            chunk_id="b",
            content="beta",
            source_url="https://example.test/b",
            record_title="Tour B",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}
    state: dict[str, Any] = {}
    page = {
        "title": "Tour A",
        "source_url": "https://example.test/a",
        "content": "## Incluye\n\nalpha page",
    }

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
            return_value=helper,
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
            return_value=page,
        ) as mock_fetch,
    ):
        result = search_context(
            "detalle",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="Tour A",
        )

    mock_search.assert_called_once_with(
        organization_slug="amaru",
        query="detalle Tour A",
        match_count=10,
    )
    mock_fetch.assert_called_once_with("https://example.test/a")
    assert result["plan_count"] == 1
    assert result["plans"] == [
        {"title": "Tour A", "source_url": "https://example.test/a"}
    ]
    assert "alpha page" in result["content"]
    assert "## Tour B" not in result["content"]
    assert result["artifact"] == []
    assert result["active_plan"] == {
        "title": "Tour A",
        "source_url": "https://example.test/a",
    }
    assert state["active_plan_url"] == "https://example.test/a"


def test_saved_plan_is_reused_without_focus_args() -> None:
    page = {
        "title": "Tour A",
        "source_url": "https://example.test/a",
        "content": "## Incluye\n\ntransporte y guía",
    }
    state = {
        "active_plan_title": "Tour A",
        "active_plan_url": "https://example.test/a",
        "active_plan_lock": "url",
        "last_plans": [
            {"title": "Tour A", "source_url": "https://example.test/a"},
            {"title": "Tour B", "source_url": "https://example.test/b"},
        ],
    }

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
            return_value=page,
        ) as mock_fetch,
    ):
        result = search_context(
            "precio",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
        )

    mock_search.assert_not_called()
    mock_fetch.assert_called_once_with("https://example.test/a")
    assert result["plan_count"] == 1
    assert result["artifact"] == []
    assert "transporte y guía" in result["content"]
    assert "## Tour A" in result["content"]
    assert "Tour B" not in result["content"]
    assert result["active_plan"] == {
        "title": "Tour A",
        "source_url": "https://example.test/a",
    }
    assert state["last_plans"][1]["title"] == "Tour B"


def test_saved_plan_missing_page_does_not_hybrid() -> None:
    state = {
        "active_plan_title": "Tour A",
        "active_plan_url": "https://example.test/a",
        "active_plan_lock": "url",
    }

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
            return_value=None,
        ),
    ):
        result = search_context(
            "incluye",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
        )

    mock_search.assert_not_called()
    assert "ficha_no_disponible: true" in result["content"]
    assert result["plan_count"] == 0
    assert result["artifact"] == []
    assert result["active_plan"] == {
        "title": "Tour A",
        "source_url": "https://example.test/a",
    }
    assert state["active_plan_url"] == "https://example.test/a"


def test_empty_helper_result_is_passed_through() -> None:
    with patch(
        "app.subagents.customer.tools.search_context.run_knowledge_search",
        return_value=dict(_EMPTY_RESULT),
    ):
        result = search_context("nada")

    assert result == _EMPTY_RESULT
    assert "plan_count" not in result


def test_shared_title_prefix_keeps_sibling_plans() -> None:
    artifact = [
        _chunk(
            chunk_id="base",
            content="ficha base",
            source_url="https://example.test/cerro",
            record_title="Cerro Azul",
        ),
        _chunk(
            chunk_id="travesia",
            content="ficha travesia",
            source_url="https://example.test/cerro-travesia",
            record_title="Cerro Azul Travesia",
        ),
        _chunk(
            chunk_id="finca",
            content="ficha finca",
            source_url="https://example.test/cerro-finca",
            record_title="Cerro Azul Finca",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}
    state = {
        "active_plan_title": "Cerro Azul",
        "active_plan_url": "https://example.test/cerro",
    }

    with patch(
        "app.subagents.customer.tools.search_context.run_knowledge_search",
        return_value=helper,
    ):
        result = search_context(
            "cerro azul",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="Cerro Azul",
        )

    assert result["plan_count"] == 3
    assert result["active_plan"] is None
    assert state["active_plan_url"] == ""
    assert "## Cerro Azul" in result["content"]
    assert "## Cerro Azul Travesia" in result["content"]
    assert "## Cerro Azul Finca" in result["content"]
    assert len(result["artifact"]) == 3


def test_saved_shared_title_follow_up_keeps_page() -> None:
    page = {
        "title": "Cerro Azul",
        "source_url": "https://example.test/cerro",
        "content": "ficha base completa",
    }
    state = {
        "active_plan_title": "Cerro Azul",
        "active_plan_url": "https://example.test/cerro",
        "active_plan_lock": "url",
    }

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
            return_value=page,
        ),
    ):
        result = search_context(
            "mas info",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
        )

    mock_search.assert_not_called()
    assert result["plan_count"] == 1
    assert "ficha base completa" in result["content"]
    assert "Cerro Azul Travesia" not in result["content"]
    assert state["active_plan_url"] == "https://example.test/cerro"


_PAGE_A = {
    "title": "Tour A",
    "source_url": "https://example.test/a",
    "content": "## Incluye\n\nguía y transporte",
}


def test_plan_focus_url_fetches_page_without_hybrid() -> None:
    state: dict[str, Any] = {}
    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
            return_value=_PAGE_A,
        ) as mock_fetch,
    ):
        result = search_context(
            "detalle",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="https://example.test/a",
        )

    mock_search.assert_not_called()
    mock_fetch.assert_called_once_with("https://example.test/a")
    assert result["plan_count"] == 1
    assert result["artifact"] == []
    assert "guía y transporte" in result["content"]
    assert state["active_plan_url"] == "https://example.test/a"


def test_plan_focus_name_reuses_last_plans_url() -> None:
    state: dict[str, Any] = {
        "last_plans": [
            {"title": "Tour A", "source_url": "https://example.test/a"},
            {"title": "Tour B", "source_url": "https://example.test/b"},
        ]
    }
    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
            return_value=_PAGE_A,
        ) as mock_fetch,
    ):
        result = search_context(
            "incluye",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="Tour A",
        )

    mock_search.assert_not_called()
    mock_fetch.assert_called_once_with("https://example.test/a")
    assert result["artifact"] == []
    assert state["active_plan_url"] == "https://example.test/a"
    assert state["last_plans"][1]["title"] == "Tour B"


def test_plan_focus_name_without_list_hybrid_then_fetch() -> None:
    artifact = [
        _chunk(
            chunk_id="a",
            content="chunk recortado",
            source_url="https://example.test/a",
            record_title="Tour A",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}
    state: dict[str, Any] = {}

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
            return_value=helper,
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
            return_value=_PAGE_A,
        ) as mock_fetch,
    ):
        result = search_context(
            "detalle",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="Tour A",
        )

    mock_search.assert_called_once()
    mock_fetch.assert_called_once_with("https://example.test/a")
    assert result["artifact"] == []
    assert "guía y transporte" in result["content"]
    assert "chunk recortado" not in result["content"]
    assert state["active_plan_url"] == "https://example.test/a"
    assert state["last_plans"] == [
        {"title": "Tour A", "source_url": "https://example.test/a"}
    ]


def test_ambiguous_family_name_does_not_fetch_or_save_url() -> None:
    state: dict[str, Any] = {
        "last_plans": [
            {"title": "Cerro Azul", "source_url": "https://example.test/cerro"},
            {
                "title": "Cerro Azul Travesia",
                "source_url": "https://example.test/cerro-travesia",
            },
        ]
    }
    artifact = [
        _chunk(
            chunk_id="base",
            content="ficha base",
            source_url="https://example.test/cerro",
            record_title="Cerro Azul",
        ),
        _chunk(
            chunk_id="travesia",
            content="ficha travesia",
            source_url="https://example.test/cerro-travesia",
            record_title="Cerro Azul Travesia",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
            return_value=helper,
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
        ) as mock_fetch,
    ):
        result = search_context(
            "cerro azul",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="Cerro Azul",
        )

    mock_search.assert_called_once()
    mock_fetch.assert_not_called()
    assert result["plan_count"] >= 2
    assert not state.get("active_plan_url")
    assert result["active_plan"] is None


def test_explore_uses_catalog_not_page_fetch() -> None:
    artifact = [
        _chunk(
            chunk_id="a",
            content="alpha",
            source_url="https://example.test/a",
            record_title="Tour A",
        ),
        _chunk(
            chunk_id="b",
            content="beta",
            source_url="https://example.test/b",
            record_title="Tour B",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}
    state = {
        "active_plan_title": "Tour A",
        "active_plan_url": "https://example.test/a",
        "active_plan_lock": "url",
    }

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
            return_value=helper,
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
        ) as mock_fetch,
    ):
        result = search_context(
            "opciones",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="Tour A",
            explore=True,
        )

    mock_search.assert_called_once()
    mock_fetch.assert_not_called()
    assert result["plan_count"] == 2
    assert result["active_plan"] is None
    assert state["active_plan_url"] == ""
    assert state["last_plans"] == [
        {"title": "Tour A", "source_url": "https://example.test/a"},
        {"title": "Tour B", "source_url": "https://example.test/b"},
    ]


def test_open_single_hit_does_not_fetch_page() -> None:
    artifact = [
        _chunk(
            chunk_id="a",
            content="alpha",
            source_url="https://example.test/a",
            record_title="Tour A",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
            return_value=helper,
        ) as mock_search,
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
        ) as mock_fetch,
    ):
        result = search_context("tour a")

    mock_search.assert_called_once()
    mock_fetch.assert_not_called()
    assert result["plan_count"] == 1
    assert "alpha" in result["content"]
    assert result["active_plan"] is None
    assert len(result["artifact"]) == 1


def test_exact_longer_title_wins_over_family_containment() -> None:
    artifact = [
        _chunk(
            chunk_id="base",
            content="ficha base",
            source_url="https://example.test/tour",
            record_title="Tour",
        ),
        _chunk(
            chunk_id="premium",
            content="ficha premium",
            source_url="https://example.test/tour-premium",
            record_title="Tour Premium",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}
    state = {
        "active_plan_title": "Tour",
        "active_plan_url": "https://example.test/tour",
    }
    page = {
        "title": "Tour Premium",
        "source_url": "https://example.test/tour-premium",
        "content": "ficha premium completa",
    }

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
            return_value=helper,
        ),
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
            return_value=page,
        ) as mock_fetch,
    ):
        result = search_context(
            "tour premium",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="Tour Premium",
        )

    mock_fetch.assert_called_once_with("https://example.test/tour-premium")
    assert result["plan_count"] == 1
    assert "ficha premium completa" in result["content"]
    assert state["active_plan_url"] == "https://example.test/tour-premium"


def test_unmatched_focus_does_not_fetch_the_only_search_hit() -> None:
    artifact = [
        _chunk(
            chunk_id="b",
            content="ficha camping",
            source_url="https://example.test/camping",
            record_title="Camping",
        ),
    ]
    helper = {"content": "raw", "artifact": deepcopy(artifact)}

    with (
        patch(
            "app.subagents.customer.tools.search_context.run_knowledge_search",
            return_value=helper,
        ),
        patch(
            "app.subagents.customer.tools.search_context.fetch_published_plan",
        ) as mock_fetch,
    ):
        result = search_context(
            "laguna",
            plan_focus="Laguna Verde",
        )

    mock_fetch.assert_not_called()
    assert result["plan_count"] == 1
    assert result["plans"] == [
        {"title": "Camping", "source_url": "https://example.test/camping"}
    ]
    assert "ficha camping" in result["content"]


def test_missing_new_url_does_not_keep_previous_active_plan() -> None:
    state = {
        "active_plan_title": "Tour B",
        "active_plan_url": "https://example.test/b",
        "active_plan_lock": "url",
    }

    with patch(
        "app.subagents.customer.tools.search_context.fetch_published_plan",
        return_value=None,
    ):
        result = search_context(
            "tour a",
            tool_context=_Ctx(state),  # type: ignore[arg-type]
            plan_focus="https://example.test/a",
        )

    assert "ficha_no_disponible: true" in result["content"]
    assert result["active_plan"] == {
        "title": "",
        "source_url": "https://example.test/a",
    }
    assert "Tour B" not in str(result["active_plan"])
    assert state["active_plan_url"] == "https://example.test/a"
    assert state["active_plan_title"] == ""
