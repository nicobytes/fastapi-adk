from __future__ import annotations

from typing import Any

from app.conversations.types import InboxMessage


def to_inbox(messages: list[InboxMessage]) -> list[dict[str, Any]]:
    return [
        {
            "id": message.id,
            "conversationId": message.conversation_id,
            "role": message.role.value,
            "kind": message.kind.value,
            "body": message.body,
            "payload": message.payload,
            "source": message.source,
            "createdAt": message.created_at.isoformat(),
        }
        for message in messages
    ]
