from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationStatus(StrEnum):
    BOT_AUTO = "BOT_AUTO"
    WAITING_HUMAN = "WAITING_HUMAN"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    CLOSED = "CLOSED"


class MessageRole(StrEnum):
    CUSTOMER = "customer"
    BOT = "bot"
    OPERATOR = "operator"


class MessageKind(StrEnum):
    TEXT = "text"
    BUTTONS = "buttons"
    LIST = "list"
    LOCATION = "location"
    MEDIA = "media"
    CHOICE = "choice"


class Conversation(BaseModel):
    id: str
    status: ConversationStatus
    wa_id: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InboxMessage(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    kind: MessageKind
    body: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChoiceOption(BaseModel):
    id: str
    title: str


def new_uuid() -> str:
    from uuid import uuid4

    return str(uuid4())


def ensure_uuid(value: str) -> str:
    UUID(value)
    return value
