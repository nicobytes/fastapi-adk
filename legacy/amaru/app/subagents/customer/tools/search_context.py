from __future__ import annotations

import re
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from google.adk.tools.tool_context import ToolContext

from app.subagents.customer.tools.fetch_published_plan import fetch_published_plan
from chatty_agent_common.knowledge_search import run_knowledge_search

_ORG_SLUG = "amaru"
_ACTIVE_TITLE = "active_plan_title"
_ACTIVE_URL = "active_plan_url"
_ACTIVE_LOCK = "active_plan_lock"
_LAST_PLANS = "last_plans"
_UNKNOWN_CHUNK = 10**9

_PLAN_RE = re.compile(
    r"(?:^|[\s*])plan\*{0,2}\s*[:\-]\s*(.+?)(?=\s+\*{1,2}[^\s*]|\s*$)",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class _PlanGroup:
    identity: str
    title: str
    source_url: str
    items: list[dict[str, Any]]


def _metadata(item: dict[str, Any]) -> dict[str, Any]:
    meta = item.get("metadata")
    return meta if isinstance(meta, dict) else {}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(raw: str) -> str:
    text = raw.replace("*", " ")
    return re.sub(r"\s+", " ", text).strip(" :-")


def _plan_line(text: str) -> str:
    match = _PLAN_RE.search(text)
    if not match:
        return ""
    return _clean_title(match.group(1))


def _source_url(item: dict[str, Any]) -> str:
    return str(_metadata(item).get("source_url") or "").strip()


def _slug_title(url: str) -> str:
    path = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return path.replace("-", " ").replace("_", " ").strip()


def _plan_identity(item: dict[str, Any]) -> str:
    url = _source_url(item)
    if url:
        return f"url:{url}"
    meta = _metadata(item)
    title = str(meta.get("record_title") or "").strip()
    if title:
        return f"title:{title}"
    heading = str(meta.get("heading") or "").strip()
    if heading:
        return f"heading:{heading}"
    plan = _plan_line(str(item.get("content") or ""))
    if plan:
        return f"plan:{plan}"
    return f"anon:{id(item)}"


def _group_title(items: list[dict[str, Any]]) -> str:
    for item in items:
        title = str(_metadata(item).get("record_title") or "").strip()
        if title:
            return _clean_title(title)
    for item in items:
        plan = _plan_line(str(item.get("content") or ""))
        if plan:
            return plan
    for item in items:
        heading = str(_metadata(item).get("heading") or "").strip()
        if heading:
            return _clean_title(heading)
    url = _source_url(items[0]) if items else ""
    slug = _slug_title(url) if url else ""
    return slug or "Plan"


def _group_plans(artifact: list[dict[str, Any]]) -> list[_PlanGroup]:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for item in artifact:
        grouped.setdefault(_plan_identity(item), []).append(item)
    groups: list[_PlanGroup] = []
    for identity, items in grouped.items():
        url = next((_source_url(item) for item in items if _source_url(item)), "")
        groups.append(
            _PlanGroup(
                identity=identity,
                title=_group_title(items),
                source_url=url,
                items=_sorted_chunks(items),
            )
        )
    return groups


def _sorted_chunks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(pair: tuple[int, dict[str, Any]]) -> tuple[int, int]:
        index, item = pair
        raw = _metadata(item).get("chunk_index")
        if isinstance(raw, bool) or not isinstance(raw, int | str):
            order = _UNKNOWN_CHUNK
        else:
            try:
                order = int(raw)
            except ValueError:
                order = _UNKNOWN_CHUNK
        return (order, index)

    return [item for _, item in sorted(enumerate(items), key=key)]


def _chunk_block(item: dict[str, Any]) -> str:
    heading = str(_metadata(item).get("heading") or "").strip()
    text = str(item.get("content") or "").strip()
    if heading:
        return f"### {heading}\n\n{text}".rstrip()
    return text


def format_grouped_content(groups: list[_PlanGroup]) -> str:
    blocks: list[str] = [f"planes_encontrados: {len(groups)}"]
    for group in groups:
        url = group.source_url or "(none)"
        body = "\n\n".join(
            _chunk_block(item) for item in group.items if item.get("content")
        )
        blocks.append(f"## {group.title}\nurl: {url}\n\n{body}".rstrip())
    return "\n\n".join(blocks)


def _state(tool_context: ToolContext | None) -> Any:
    if tool_context is None:
        return None
    return getattr(tool_context, "state", None)


def _read_active(state: Any) -> tuple[str, str]:
    if state is None:
        return "", ""
    title = str(state.get(_ACTIVE_TITLE) or "").strip()
    url = str(state.get(_ACTIVE_URL) or "").strip()
    return title, url


def _write_active(state: Any, group: _PlanGroup, lock: str) -> None:
    if state is None:
        return
    state[_ACTIVE_TITLE] = group.title
    state[_ACTIVE_URL] = group.source_url
    state[_ACTIVE_LOCK] = lock


def _clear_active(state: Any) -> None:
    if state is None:
        return
    state[_ACTIVE_TITLE] = ""
    state[_ACTIVE_URL] = ""
    state[_ACTIVE_LOCK] = ""


def _replace_active_with_missing(
    state: Any,
    url: str,
    lock: str,
    title_hint: str = "",
) -> None:
    """Point active state at the requested focus so a miss cannot leak the previous plan."""
    if state is None:
        return
    previous_url = str(state.get(_ACTIVE_URL) or "").strip()
    requested = url.strip()
    state[_ACTIVE_URL] = requested
    if title_hint:
        state[_ACTIVE_TITLE] = title_hint
    elif previous_url != requested:
        state[_ACTIVE_TITLE] = ""
    state[_ACTIVE_LOCK] = lock


def _active_payload(state: Any) -> dict[str, str] | None:
    title, url = _read_active(state)
    if not title and not url:
        return None
    return {"title": title, "source_url": url}


def _read_last_plans(state: Any) -> list[dict[str, str]]:
    if state is None:
        return []
    raw = state.get(_LAST_PLANS)
    if not isinstance(raw, list):
        return []
    plans: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("source_url") or "").strip()
        if title or url:
            plans.append({"title": title, "source_url": url})
    return plans


def _write_last_plans(state: Any, plans: list[dict[str, str]]) -> None:
    if state is None:
        return
    state[_LAST_PLANS] = [
        {
            "title": str(item.get("title") or ""),
            "source_url": str(item.get("source_url") or ""),
        }
        for item in plans
    ]


def _groups_from_last_plans(plans: list[dict[str, str]]) -> list[_PlanGroup]:
    groups: list[_PlanGroup] = []
    for item in plans:
        title = str(item.get("title") or "").strip() or "Plan"
        url = str(item.get("source_url") or "").strip()
        identity = f"url:{url}" if url else f"title:{title}"
        groups.append(
            _PlanGroup(identity=identity, title=title, source_url=url, items=[])
        )
    return groups


def _page_digest(
    *,
    title: str,
    source_url: str,
    markdown: str,
    state: Any,
) -> dict[str, Any]:
    body = markdown.strip()
    content = (
        f"planes_encontrados: 1\n\n## {title}\nurl: {source_url}\n\n{body}".rstrip()
    )
    return {
        "plan_count": 1,
        "plans": [{"title": title, "source_url": source_url}],
        "content": content,
        "active_plan": _active_payload(state),
        "artifact": [],
    }


def _unavailable_digest(reason: str, state: Any) -> dict[str, Any]:
    label = reason if reason in {"missing", "empty", "inactive"} else "missing"
    return {
        "plan_count": 0,
        "plans": [],
        "content": f"ficha_no_disponible: true\nreason: {label}",
        "active_plan": _active_payload(state),
        "artifact": [],
    }


def _is_explore(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "si", "sí"}
    return value is True


def _looks_like_url(value: str) -> bool:
    folded = value.strip().casefold()
    return folded.startswith(("http://", "https://"))


def _boost_query(query: str, label: str) -> str:
    cleaned = label.strip()
    if not cleaned or _looks_like_url(cleaned):
        return query
    if _fold(cleaned) in _fold(query):
        return query
    return f"{query} {cleaned}".strip()


def _tokens(value: str) -> list[str]:
    return [token for token in _TOKEN_RE.split(_fold(value)) if len(token) >= 4]


def _title_matches(title: str, focus: str) -> bool:
    folded_title = _fold(title)
    folded_focus = _fold(focus)
    if not folded_title or not folded_focus:
        return False
    if folded_title == folded_focus:
        return True
    if len(folded_focus) >= 4 and (
        folded_focus in folded_title or folded_title in folded_focus
    ):
        return True
    focus_tokens = _tokens(focus)
    title_tokens = set(_tokens(title))
    if not focus_tokens or not title_tokens:
        return False
    return all(token in title_tokens for token in focus_tokens)


def _url_matches(url: str, focus: str) -> bool:
    left = url.strip().rstrip("/").casefold()
    right = focus.strip().rstrip("/").casefold()
    return bool(left) and left == right


def _title_contains(title: str, focus: str) -> bool:
    folded_title = _fold(title)
    folded_focus = _fold(focus)
    if not folded_title or not folded_focus or len(folded_focus) < 4:
        return False
    return folded_focus in folded_title or folded_title in folded_focus


def _family_matches(groups: list[_PlanGroup], focus: str) -> list[_PlanGroup]:
    return [group for group in groups if _title_contains(group.title, focus)]


def _title_shared_with_sibling(group: _PlanGroup, groups: list[_PlanGroup]) -> bool:
    folded = _fold(group.title)
    if len(folded) < 4:
        return False
    return any(
        other.identity != group.identity and folded in _fold(other.title)
        for other in groups
    )


def _select_plan(groups: list[_PlanGroup], focus: str) -> _PlanGroup | None:
    needle = focus.strip()
    if not needle:
        return None
    if _looks_like_url(needle):
        hits = [group for group in groups if _url_matches(group.source_url, needle)]
        return hits[0] if len(hits) == 1 else None
    family = _family_matches(groups, needle)
    if len(family) == 1 and not _title_shared_with_sibling(family[0], groups):
        return family[0]
    exact = [group for group in groups if _fold(group.title) == _fold(needle)]
    if (
        len(exact) == 1
        and not _title_shared_with_sibling(exact[0], groups)
        and _title_matches(exact[0].title, needle)
    ):
        return exact[0]
    hits = [group for group in groups if _title_matches(group.title, needle)]
    if len(hits) == 1 and not _title_shared_with_sibling(hits[0], groups):
        return hits[0]
    return None


def _plan_index(groups: list[_PlanGroup]) -> list[dict[str, str]]:
    return [{"title": group.title, "source_url": group.source_url} for group in groups]


def _digest(
    groups: list[_PlanGroup],
    artifact: list[dict[str, Any]],
    state: Any,
) -> dict[str, Any]:
    return {
        "plan_count": len(groups),
        "plans": _plan_index(groups),
        "content": format_grouped_content(groups),
        "active_plan": _active_payload(state),
        "artifact": artifact,
    }


def _respond_with_url(
    url: str,
    state: Any,
    lock: str,
    title_hint: str = "",
) -> dict[str, Any]:
    page = fetch_published_plan(url)
    if page is None:
        _replace_active_with_missing(state, url, lock, title_hint)
        return _unavailable_digest("missing", state)
    group = _PlanGroup(
        identity=f"url:{page['source_url']}",
        title=page["title"],
        source_url=page["source_url"],
        items=[],
    )
    _write_active(state, group, lock)
    return _page_digest(
        title=page["title"],
        source_url=page["source_url"],
        markdown=page["content"],
        state=state,
    )


def _run_catalog(
    search_query: str,
    match_count: int,
    state: Any,
    *,
    mode: str,
    focus: str = "",
    stored_title: str = "",
    stored_url: str = "",
) -> dict[str, Any]:
    result = run_knowledge_search(
        organization_slug=_ORG_SLUG,
        query=search_query,
        match_count=match_count,
    )
    artifact = result.get("artifact")
    if not artifact:
        return result

    groups = _group_plans(artifact)
    _write_last_plans(state, _plan_index(groups))
    visible = groups

    if mode == "focus":
        if not _looks_like_url(focus):
            selected = _select_plan(groups, focus)
            if selected is not None and selected.source_url:
                return _respond_with_url(
                    selected.source_url,
                    state,
                    "title",
                    selected.title,
                )
            if selected is not None:
                _write_active(state, selected, "title")
                visible = [selected]
            else:
                family = _family_matches(groups, focus)
                if len(family) > 1:
                    _clear_active(state)
                    visible = family
        else:
            selected = _select_plan(groups, focus)
            if selected is not None and selected.source_url:
                return _respond_with_url(selected.source_url, state, "url")
    elif mode == "reuse":
        selected = _select_plan(groups, stored_url or stored_title)
        lock = str(state.get(_ACTIVE_LOCK) or "") if state is not None else ""
        shared = selected is not None and _title_shared_with_sibling(selected, groups)
        if selected is not None and shared and lock != "url":
            family = _family_matches(groups, selected.title)
            _clear_active(state)
            visible = family if len(family) > 1 else groups
        elif selected is not None and selected.source_url:
            return _respond_with_url(
                selected.source_url,
                state,
                lock or "title",
                selected.title,
            )
        elif selected is not None:
            _write_active(state, selected, lock or "title")
            visible = [selected]

    return _digest(visible, artifact, state)


def search_context(
    query: str,
    tool_context: ToolContext | None = None,
    matchCount: int = 10,
    plan_focus: str | None = None,
    explore: bool = False,
) -> dict[str, Any]:
    """Busca planes y tours en la base de conocimiento de Xperiencia.

    Úsala cuando necesites datos concretos de planes o tours: exploración por
    destino o tema, seguimiento de un plan ya elegido, o un nombre literal del sitio.

    Lee `plan_count`, `plans`, `content` y `active_plan`. Ignora `artifact`.

    Args:
        query: Consulta (destino, tema, o detalle del plan).
        matchCount: Fragmentos a recuperar (1-20).
        plan_focus: Nombre, apodo o url de **un** tour ya elegido. Filtra el set
            a esa ficha y lo guarda. Si el nombre es prefijo de otras fichas del
            set, no filtra: son hermanos, no un solo plan.
        explore: True en catálogo, destino, mes, tema, "otras opciones" u otro
            destino. Limpia el plan guardado y no filtra. Gana sobre `plan_focus`.

    Follow-up del mismo plan ("¿incluye?", "¿precio?"): no pases `explore` ni
    `plan_focus`; se reusa el plan guardado. Si la respuesta es ambigua ("ese",
    el nombre de la familia), no pases `plan_focus`: pregunta cuál.
    """
    state = _state(tool_context)
    exploring = _is_explore(explore)
    focus = "" if exploring else (plan_focus or "").strip()
    stored_title, stored_url = _read_active(state)

    if exploring:
        _clear_active(state)
        return _run_catalog(query, matchCount, state, mode="explore")

    if focus:
        if _looks_like_url(focus):
            return _respond_with_url(focus, state, "url")
        selected = _select_plan(_groups_from_last_plans(_read_last_plans(state)), focus)
        if selected is not None and selected.source_url:
            return _respond_with_url(
                selected.source_url,
                state,
                "title",
                selected.title,
            )
        return _run_catalog(
            _boost_query(query, focus),
            matchCount,
            state,
            mode="focus",
            focus=focus,
        )

    if stored_url:
        lock = str(state.get(_ACTIVE_LOCK) or "") if state is not None else ""
        return _respond_with_url(stored_url, state, lock or "url", stored_title)

    if stored_title:
        return _run_catalog(
            _boost_query(query, stored_title),
            matchCount,
            state,
            mode="reuse",
            stored_title=stored_title,
            stored_url=stored_url,
        )

    return _run_catalog(query, matchCount, state, mode="open")
