from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis


def buffer_key(conversation_id: str) -> str:
    return f"buffer:{conversation_id}"


async def push_text(redis: Redis, conversation_id: str, text: str) -> None:
    await redis.rpush(buffer_key(conversation_id), text)  # type: ignore[misc]


async def drain_texts(redis: Redis, conversation_id: str) -> list[str]:
    key = buffer_key(conversation_id)
    async with redis.pipeline(transaction=True) as pipe:
        pipe.lrange(key, 0, -1)
        pipe.delete(key)
        results = await pipe.execute()
    raw_items: list[Any] = results[0] or []
    texts: list[str] = []
    for item in raw_items:
        if isinstance(item, bytes):
            item = item.decode("utf-8")
        texts.append(str(item))
    return texts


async def buffer_length(redis: Redis, conversation_id: str) -> int:
    return int(await redis.llen(buffer_key(conversation_id)))  # type: ignore[misc]
