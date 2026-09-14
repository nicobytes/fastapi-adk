from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from arq.worker import Worker
from redis.asyncio import Redis

from app.adk.host import AdkHost
from app.channel.service import ChannelService
from app.config import Settings
from app.conversations.store import ConversationStore
from app.queue.conversation_lock import ConversationLock
from app.queue.turn import TurnService
from app.queue.worker import WorkerSettings, process_turn, set_app_state


@dataclass
class AppState:
    settings: Settings
    store: ConversationStore
    channel: ChannelService
    host: AdkHost
    turn_service: TurnService
    conversation_lock: ConversationLock
    redis: Redis
    arq: ArqRedis
    worker: Worker | None = None
    worker_task: Any = None


async def build_app_state(settings: Settings | None = None) -> AppState:
    settings = settings or Settings()
    store = ConversationStore(settings.poc_db_url)
    await store.connect()
    channel = ChannelService(store)
    host = AdkHost(
        session_db_url=settings.session_db_url,
        channel=channel,
        store=store,
        google_api_key=settings.google_api_key,
    )
    await host.prepare()
    turn_service = TurnService(host, store, channel)
    conversation_lock = ConversationLock()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    state = AppState(
        settings=settings,
        store=store,
        channel=channel,
        host=host,
        turn_service=turn_service,
        conversation_lock=conversation_lock,
        redis=redis,
        arq=arq,
    )
    set_app_state(state)

    if settings.embed_worker:
        worker = Worker(
            functions=[process_turn],
            redis_settings=RedisSettings.from_dsn(settings.redis_url),
            queue_name=settings.queue_name,
            on_startup=WorkerSettings.on_startup,
            max_tries=3,
            keep_result=0,
            handle_signals=False,
            ctx={"app_state": state},
            poll_delay=0.1,
        )
        state.worker = worker
        state.worker_task = asyncio.create_task(worker.async_run())

    return state


async def shutdown_app_state(state: AppState) -> None:
    """Best-effort shutdown; never block forever on the embedded worker."""
    worker = state.worker
    task = state.worker_task
    state.worker = None
    state.worker_task = None

    if worker is not None:
        # Signal stop without awaiting job completion
        worker.closing = True  # type: ignore[attr-defined]
        if getattr(worker, "main_task", None):
            worker.main_task.cancel()
        for job_task in list(getattr(worker, "tasks", ()) or []):
            if hasattr(job_task, "cancel"):
                job_task.cancel()

    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except BaseException:
            pass

    for closer in (getattr(state.arq, "aclose", None), getattr(state.arq, "close", None)):
        if closer is None:
            continue
        try:
            result = closer(close_connection_pool=True)
            if asyncio.iscoroutine(result):
                await asyncio.wait_for(result, timeout=1)
            break
        except Exception:
            continue

    try:
        await asyncio.wait_for(state.redis.aclose(), timeout=1)
    except Exception:
        pass
    try:
        await state.store.close()
    except Exception:
        pass

