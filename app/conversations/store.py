from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiosqlite

from app.conversations.types import (
    Conversation,
    ConversationStatus,
    InboxMessage,
    MessageKind,
    MessageRole,
    new_uuid,
)


def _sqlite_path(db_url: str) -> str:
    # sqlite+aiosqlite:///./data/poc.sqlite or sqlite+aiosqlite:////abs/path
    raw = db_url.replace("sqlite+aiosqlite:///", "", 1)
    if raw.startswith("./") or (not raw.startswith("/") and "://" not in raw):
        path = Path(raw)
    else:
        path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


class ConversationStore:
    def __init__(self, db_url: str) -> None:
        self._path = _sqlite_path(db_url)
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
              id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              wa_id TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_wa_open
              ON conversations(wa_id) WHERE status != 'CLOSED';

            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              role TEXT NOT NULL,
              kind TEXT NOT NULL,
              body TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              source TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
              ON messages(conversation_id, created_at);

            CREATE TABLE IF NOT EXISTS sent_tool_calls (
              id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              tool_name TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS whatsapp_dedup (
              message_id TEXT PRIMARY KEY,
              seen_at TEXT NOT NULL
            );
            """
        )
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _db(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("ConversationStore not connected")
        return self._conn

    async def find_or_create_open(self, wa_id: str) -> Conversation:
        db = self._db()
        cur = await db.execute(
            "SELECT * FROM conversations WHERE wa_id = ? AND status != 'CLOSED' "
            "ORDER BY updated_at DESC LIMIT 1",
            (wa_id,),
        )
        row = await cur.fetchone()
        if row:
            return self._row_to_conversation(row)
        now = datetime.now(timezone.utc).isoformat()
        conversation_id = new_uuid()
        await db.execute(
            "INSERT INTO conversations (id, status, wa_id, updated_at) VALUES (?, ?, ?, ?)",
            (conversation_id, ConversationStatus.BOT_AUTO.value, wa_id, now),
        )
        await db.commit()
        return Conversation(
            id=conversation_id,
            status=ConversationStatus.BOT_AUTO,
            wa_id=wa_id,
            updated_at=datetime.fromisoformat(now),
        )

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        cur = await self._db().execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        )
        row = await cur.fetchone()
        return self._row_to_conversation(row) if row else None

    async def set_status(
        self, conversation_id: str, status: ConversationStatus
    ) -> Conversation:
        now = datetime.now(timezone.utc).isoformat()
        await self._db().execute(
            "UPDATE conversations SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, now, conversation_id),
        )
        await self._db().commit()
        conversation = await self.get_by_id(conversation_id)
        if conversation is None:
            raise KeyError(conversation_id)
        return conversation

    async def touch(self, conversation_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db().execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        await self._db().commit()

    async def insert_message(
        self,
        *,
        conversation_id: str,
        role: MessageRole,
        kind: MessageKind,
        body: str,
        payload: dict[str, Any] | None = None,
        source: str | None = None,
    ) -> InboxMessage:
        message_id = new_uuid()
        now = datetime.now(timezone.utc).isoformat()
        payload = payload or {}
        await self._db().execute(
            "INSERT INTO messages "
            "(id, conversation_id, role, kind, body, payload_json, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                message_id,
                conversation_id,
                role.value,
                kind.value,
                body,
                json.dumps(payload),
                source,
                now,
            ),
        )
        await self._db().commit()
        await self.touch(conversation_id)
        return InboxMessage(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            kind=kind,
            body=body,
            payload=payload,
            source=source,
            created_at=datetime.fromisoformat(now),
        )

    async def list_messages(self, conversation_id: str) -> list[InboxMessage]:
        cur = await self._db().execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )
        rows = await cur.fetchall()
        return [self._row_to_message(row) for row in rows]

    async def mark_tool_sent(
        self, function_call_id: str, conversation_id: str, tool_name: str
    ) -> bool:
        """Return True if newly marked; False if already sent."""
        cur = await self._db().execute(
            "SELECT id FROM sent_tool_calls WHERE id = ?", (function_call_id,)
        )
        if await cur.fetchone():
            return False
        now = datetime.now(timezone.utc).isoformat()
        await self._db().execute(
            "INSERT INTO sent_tool_calls (id, conversation_id, tool_name, created_at) "
            "VALUES (?, ?, ?, ?)",
            (function_call_id, conversation_id, tool_name, now),
        )
        await self._db().commit()
        return True

    async def was_tool_sent(self, function_call_id: str) -> bool:
        cur = await self._db().execute(
            "SELECT id FROM sent_tool_calls WHERE id = ?", (function_call_id,)
        )
        return await cur.fetchone() is not None

    async def take_whatsapp_message(self, message_id: str) -> bool:
        """Return True if first time seeing message_id."""
        cur = await self._db().execute(
            "SELECT message_id FROM whatsapp_dedup WHERE message_id = ?",
            (message_id,),
        )
        if await cur.fetchone():
            return False
        now = datetime.now(timezone.utc).isoformat()
        await self._db().execute(
            "INSERT INTO whatsapp_dedup (message_id, seen_at) VALUES (?, ?)",
            (message_id, now),
        )
        await self._db().commit()
        return True

    @staticmethod
    def _row_to_conversation(row: aiosqlite.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            status=ConversationStatus(row["status"]),
            wa_id=row["wa_id"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_message(row: aiosqlite.Row) -> InboxMessage:
        return InboxMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=MessageRole(row["role"]),
            kind=MessageKind(row["kind"]),
            body=row["body"],
            payload=json.loads(row["payload_json"] or "{}"),
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
