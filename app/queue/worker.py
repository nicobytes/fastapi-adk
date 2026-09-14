from __future__ import annotations

import logging
from typing import Any

from arq import Retry
from arq.connections import RedisSettings

from app.constants import QUEUE_NAME
from app.queue import buffer as message_buffer
from app.queue.enqueue import enqueue_follow_up

logger = logging.getLogger(__name__)

# Set by FastAPI lifespan so in-process / CLI workers share services.
_APP_STATE: Any | None = None


def set_app_state(state: Any) -> None:
    global _APP_STATE
    _APP_STATE = state


def get_app_state() -> Any:
    if _APP_STATE is None:
        raise RuntimeError("App state not initialized for queue worker")
    return _APP_STATE


async def process_turn(
    ctx: dict[str, Any],
    conversation_id: str,
    kind: str,
    text: str | None = None,
    button_id: str | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    state = ctx.get("app_state") or get_app_state()
    turn = state.turn_service
    redis = state.redis
    lock = state.conversation_lock.for_conversation(conversation_id)

    async with lock:
        try:
            if kind == "button":
                assert button_id is not None
                result = await turn.run_button_turn(
                    conversation_id=conversation_id,
                    button_id=button_id,
                    agent_id=agent_id,
                )
                return {"ok": True, "skipped": result.skipped, "reason": result.reason}

            # Text turn: drain buffer (may include the triggering texts)
            texts = await message_buffer.drain_texts(redis, conversation_id)
            if text:
                texts.append(text)
            if not texts:
                return {"ok": True, "empty": True}
            combined = "\n".join(texts)
            try:
                await turn.run_text_turn(
                    conversation_id=conversation_id,
                    text=combined,
                    agent_id=agent_id,
                )
            except Exception as exc:
                # Re-queue drained texts so retries still see customer input
                for item in texts:
                    await message_buffer.push_text(redis, conversation_id, item)
                job_try = int(ctx.get("job_try") or 1)
                logger.exception("process_turn failed try=%s: %s", job_try, exc)
                if job_try < 3:
                    raise Retry(defer=1) from exc
                raise
            # Follow-up if more text arrived while busy
            if await message_buffer.buffer_length(redis, conversation_id) > 0:
                await enqueue_follow_up(
                    state.arq,
                    conversation_id=conversation_id,
                    agent_id=agent_id,
                    queue_name=state.settings.queue_name,
                )
            return {"ok": True, "texts": len(texts)}
        except Retry:
            raise
        except Exception as exc:
            job_try = int(ctx.get("job_try") or 1)
            logger.exception("process_turn failed try=%s: %s", job_try, exc)
            if job_try < 3:
                raise Retry(defer=1) from exc
            raise


async def on_startup(ctx: dict[str, Any]) -> None:
    if _APP_STATE is not None:
        ctx["app_state"] = _APP_STATE


class WorkerSettings:
    functions = [process_turn]
    on_startup = on_startup
    max_tries = 3
    job_timeout = 300
    keep_result = 0

    @staticmethod
    def redis_settings_from(url: str) -> RedisSettings:
        return RedisSettings.from_dsn(url)

    # Defaults overwritten when embedding / CLI uses custom settings
    redis_settings = RedisSettings()
    queue_name = QUEUE_NAME
