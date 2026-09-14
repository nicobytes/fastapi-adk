from __future__ import annotations

import asyncio
from collections import defaultdict


class ConversationLock:
    """Serialize turns per conversation (clicks wait for active text turns)."""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def for_conversation(self, conversation_id: str) -> asyncio.Lock:
        return self._locks[conversation_id]
