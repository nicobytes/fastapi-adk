from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from app.conversations.types import ChoiceOption


@dataclass
class ChannelMessage:
    session_id: str
    kind: str
    payload: dict[str, Any]
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    target: str | None = None
    channel: str = "fake"


@runtime_checkable
class ChannelSink(Protocol):
    channel: str

    async def deliver(self, message: ChannelMessage) -> None: ...
