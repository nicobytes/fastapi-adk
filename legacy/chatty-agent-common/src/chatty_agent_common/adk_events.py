"""ADK Event helpers that Vertex Sessions will accept.

Vertex ``append_event`` rejects events with an empty ``invocation_id``
(400 INVALID_ARGUMENT: ``event.invocation_id`` required). ADK's own Event
factory always copies ``ctx.invocation_id``; custom ``Event()`` yields must
do the same.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from google.adk.events import Event
from google.genai import types

# Vertex rebuilds session.state from event actions. Empty strings serialize;
# orchestrators treat only ``"true"`` as pending.
CLEAR_ACTIVATE_STATE: dict[str, str] = {
    "activate_pending": "",
    "activate_stage": "",
    "activate_note": "",
}


class InvocationIdSource(Protocol):
    invocation_id: str
    branch: str | None


def model_text_event(
    ctx: InvocationIdSource,
    text: str,
    *,
    author: str,
    state: Mapping[str, Any] | None = None,
) -> Event:
    """Visible model text Event with the invocation id Vertex requires."""
    kwargs: dict[str, Any] = {
        "invocation_id": ctx.invocation_id,
        "author": author,
        "branch": ctx.branch,
        "content": types.Content(
            role="model",
            parts=[types.Part(text=text)],
        ),
    }
    if state is not None:
        kwargs["state"] = dict(state)
    return Event(**kwargs)


def state_delta_event(
    ctx: InvocationIdSource,
    *,
    author: str,
    state: Mapping[str, Any],
) -> Event:
    """Persist session state when there is no user-visible model text."""
    return Event(
        invocation_id=ctx.invocation_id,
        author=author,
        branch=ctx.branch,
        state=dict(state),
    )


def ensure_invocation_id(event: Event, ctx: InvocationIdSource) -> Event:
    """Fill ``invocation_id`` when a yielded Event omitted it."""
    if event.invocation_id:
        return event
    return event.model_copy(
        update={
            "invocation_id": ctx.invocation_id,
            "branch": event.branch or ctx.branch,
        }
    )
