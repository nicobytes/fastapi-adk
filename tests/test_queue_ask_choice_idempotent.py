from __future__ import annotations

import pytest

from app.conversations.store import ConversationStore


@pytest.mark.asyncio
async def test_sent_tool_calls_idempotent(tmp_path) -> None:
    store = ConversationStore(f"sqlite+aiosqlite:///{tmp_path / 'poc.sqlite'}")
    await store.connect()
    try:
        conv = await store.find_or_create_open("idem-1")
        first = await store.mark_tool_sent("fc-1", conv.id, "ask_choice")
        second = await store.mark_tool_sent("fc-1", conv.id, "ask_choice")
        assert first is True
        assert second is False
        assert await store.was_tool_sent("fc-1") is True
    finally:
        await store.close()
