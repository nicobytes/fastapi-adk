"""Filter internal qualifier JSON from LLM request contents."""

from __future__ import annotations

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from chatty_agent_common.qualification import parse_bant_signals

__all__ = [
    "filter_internal_bant_contents",
    "strip_internal_bant_contents",
]

_ACTIVATE_STIMULUS = "[CHATTY_ACTIVATE]"


def _content_text(content: types.Content) -> str | None:
    if not content.parts:
        return None
    texts: list[str] = []
    for part in content.parts:
        text = getattr(part, "text", None)
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
    if not texts:
        return None
    return "\n".join(texts)


def _is_internal_bant_content(content: types.Content) -> bool:
    text = _content_text(content)
    if text is None:
        return False
    return parse_bant_signals(text) is not None


def _is_activate_stimulus_content(content: types.Content) -> bool:
    text = _content_text(content)
    if text is None:
        return False
    return text.startswith(_ACTIVATE_STIMULUS)


def filter_internal_bant_contents(
    contents: list[types.Content],
) -> list[types.Content]:
    """Return contents with silent qualifier BANT JSON and activate tokens removed."""
    return [
        content
        for content in contents
        if not _is_internal_bant_content(content)
        and not _is_activate_stimulus_content(content)
    ]


async def strip_internal_bant_contents(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """ADK before_model_callback: drop qualifier output from LLM history."""
    del callback_context  # unused; signature fixed by ADK
    llm_request.contents = filter_internal_bant_contents(llm_request.contents)
    return None
