"""Load one Amaru published plan page by canonical source_url (no hybrid)."""

from __future__ import annotations

import re

import httpx
from postgrest.exceptions import APIError

from chatty_agent_common.providers.supabase import (
    get_organization_slug,
    get_supabase_client,
)

_ORG_SLUG = "amaru"
_USABLE_STATUSES = ("chunked", "cleaned")


def canonical_page_url(p_url: str) -> str:
    """Mirror ``util.canonical_page_url``: https, lowercase host, strip slash."""
    trimmed = (p_url or "").strip()
    if not trimmed:
        return trimmed
    try:
        hash_pos = trimmed.find("#")
        if hash_pos >= 0:
            base_part = trimmed[:hash_pos]
            fragment_part = trimmed[hash_pos + 1 :]
        else:
            base_part = trimmed
            fragment_part = None

        if not re.match(r"^https?://", base_part, re.I):
            base_part = "https://" + base_part

        scheme_match = re.match(r"^([^:]+)", base_part)
        scheme = (scheme_match.group(1) if scheme_match else "").lower()
        if scheme == "http":
            scheme = "https"
        elif scheme != "https":
            return trimmed

        rest_match = re.search(r"://(.*)$", base_part)
        if rest_match is None:
            return trimmed
        rest = rest_match.group(1)

        qpos = rest.find("?")
        if qpos >= 0:
            query = rest[qpos + 1 :]
            rest = rest[:qpos]
        else:
            query = None

        slashpos = rest.find("/")
        if slashpos >= 0:
            host = rest[:slashpos].lower()
            path = rest[slashpos:]
        else:
            host = rest.lower()
            path = "/"

        if path != "/":
            path = re.sub(r"/+$", "", path)
            if path == "":
                path = "/"

        result = f"{scheme}://{host}{path}"
        if query:
            result += "?" + query

        if fragment_part is not None and fragment_part.strip():
            fragment_part = fragment_part.strip()
            if fragment_part.startswith("/"):
                fragment_part = re.sub(r"/+$", "", fragment_part)
                if fragment_part == "":
                    fragment_part = "/"
            result += "#" + fragment_part
        return result
    except Exception:
        return trimmed


def _slug_title(url: str) -> str:
    path = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return path.replace("-", " ").replace("_", " ").strip()


def fetch_published_plan(source_url: str) -> dict[str, str] | None:
    """Return ``{title, source_url, content}`` for one usable Amaru page, or None."""
    cleaned = (source_url or "").strip()
    if not cleaned:
        return None
    canonical = canonical_page_url(cleaned)
    try:
        org_id = get_organization_slug(_ORG_SLUG)
        client = get_supabase_client()
        response = (
            client.table("knowledge_source")
            .select(
                "title,content,source_url,is_active,status,updated_at,"
                "knowledge_base!inner(is_active)"
            )
            .eq("organization_id", org_id)
            .eq("source_url", canonical)
            .eq("is_active", True)
            .in_("status", list(_USABLE_STATUSES))
            .eq("knowledge_base.is_active", True)
            .order("updated_at", desc=True)
            .limit(5)
            .execute()
        )
    except (httpx.ConnectError, RuntimeError, APIError):
        return None

    rows = response.data if isinstance(getattr(response, "data", None), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        kb = row.get("knowledge_base")
        if isinstance(kb, dict) and kb.get("is_active") is False:
            continue
        title = str(row.get("title") or "").strip() or _slug_title(canonical)
        stored_url = str(row.get("source_url") or "").strip() or canonical
        return {
            "title": title,
            "source_url": stored_url,
            "content": content,
        }
    return None
