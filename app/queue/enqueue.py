from __future__ import annotations

from typing import Any

from arq import ArqRedis
from arq.jobs import Job

from app.config import Settings
from app.constants import BUFFER_MS, QUEUE_NAME


async def enqueue_text(
    redis: ArqRedis,
    *,
    conversation_id: str,
    agent_id: str | None = None,
    buffer_ms: float | None = None,
    queue_name: str | None = None,
) -> Job | None:
    delay = BUFFER_MS if buffer_ms is None else buffer_ms
    return await redis.enqueue_job(
        "process_turn",
        conversation_id,
        "text",
        None,
        None,
        agent_id,
        _job_id=conversation_id,
        _defer_by=delay,
        _queue_name=queue_name or QUEUE_NAME,
    )


async def enqueue_button(
    redis: ArqRedis,
    *,
    conversation_id: str,
    button_id: str,
    agent_id: str | None = None,
    queue_name: str | None = None,
) -> Job | None:
    import time

    job_id = f"{conversation_id}:btn:{button_id}:{int(time.time() * 1000)}"
    return await redis.enqueue_job(
        "process_turn",
        conversation_id,
        "button",
        None,
        button_id,
        agent_id,
        _job_id=job_id,
        _defer_by=0,
        _queue_name=queue_name or QUEUE_NAME,
    )


async def enqueue_follow_up(
    redis: ArqRedis,
    *,
    conversation_id: str,
    agent_id: str | None = None,
    queue_name: str | None = None,
) -> Job | None:
    import time

    job_id = f"{conversation_id}-{int(time.time() * 1000)}"
    return await redis.enqueue_job(
        "process_turn",
        conversation_id,
        "text",
        None,
        None,
        agent_id,
        _job_id=job_id,
        _defer_by=0,
        _queue_name=queue_name or QUEUE_NAME,
    )
