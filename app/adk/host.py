from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from google.adk.apps.app import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from app.adk.ask_choice import create_ask_choice_tool
from app.adk.events import find_pending_choice
from app.agents.default import create_default_agent
from app.channel.service import ChannelService
from app.constants import APP_NAME, DEFAULT_AGENT_ID, USER_ID
from app.conversations.store import ConversationStore

logger = logging.getLogger(__name__)


@dataclass
class RunView:
    reply_text: str | None = None
    paused: bool = False
    events: list[Any] = field(default_factory=list)
    skipped: bool = False
    reason: str | None = None


class AdkHost:
    """In-process ADK Runner adapter with per-session serialization."""

    def __init__(
        self,
        *,
        session_db_url: str,
        channel: ChannelService,
        store: ConversationStore,
        google_api_key: str = "",
    ) -> None:
        if google_api_key:
            os.environ.setdefault("GOOGLE_API_KEY", google_api_key)
        self.channel = channel
        self.store = store
        self.session_service = DatabaseSessionService(db_url=session_db_url)
        tool = create_ask_choice_tool(channel, store)
        self._agent = create_default_agent(tools=[tool])
        self._app = App(
            name=APP_NAME,
            root_agent=self._agent,
            resumability_config=ResumabilityConfig(is_resumable=True),
        )
        self.runner = Runner(
            app=self._app,
            session_service=self.session_service,
            auto_create_session=True,
        )
        self._locks: dict[str, asyncio.Lock] = {}
        self.yield_delay_seconds: float = 0.0
        self.suppress_text_when_paused: bool = True
        self._ready = False

    async def prepare(self) -> None:
        if not self._ready:
            await self.session_service.prepare_tables()
            self._ready = True

    def _lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    async def ensure_session(
        self, session_id: str, *, agent_id: str = DEFAULT_AGENT_ID, user_id: str = USER_ID
    ) -> Any:
        await self.prepare()
        session = await self.session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        if session is None:
            session = await self.session_service.create_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )
        return session

    async def inbound(
        self,
        session_id: str,
        text: str,
        *,
        agent_id: str = DEFAULT_AGENT_ID,
        user_id: str = USER_ID,
        channel: str = "fake",
        target: str | None = None,
    ) -> RunView:
        self.channel.bind(session_id, channel, target)
        await self.ensure_session(session_id, agent_id=agent_id, user_id=user_id)
        if self.yield_delay_seconds > 0:
            await asyncio.sleep(self.yield_delay_seconds)
        message = types.Content(role="user", parts=[types.Part(text=text)])
        return await self._run(session_id, message, user_id=user_id)

    async def resume(
        self,
        session_id: str,
        button_id: str,
        *,
        agent_id: str = DEFAULT_AGENT_ID,
        user_id: str = USER_ID,
        channel: str = "fake",
        target: str | None = None,
    ) -> RunView:
        self.channel.bind(session_id, channel, target)
        session = await self.ensure_session(session_id, agent_id=agent_id, user_id=user_id)
        pending = find_pending_choice(session.events)
        if not pending:
            return RunView(skipped=True, reason="no_pending_choice")
        fr = types.FunctionResponse(
            id=pending["function_call_id"],
            name="ask_choice",
            response={"buttonId": button_id},
        )
        message = types.Content(role="user", parts=[types.Part(function_response=fr)])
        return await self._run(session_id, message, user_id=user_id)

    async def append_operator_text(
        self, session_id: str, text: str, *, user_id: str = USER_ID
    ) -> None:
        session = await self.ensure_session(session_id, user_id=user_id)
        # Reload to avoid stale marker
        session = await self.session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        assert session is not None
        event = Event(
            author="user",
            content=types.Content(
                role="user",
                parts=[types.Part(text=f"Operator: {text}")],
            ),
        )
        await self.session_service.append_event(session=session, event=event)

    async def _run(
        self, session_id: str, message: types.Content, *, user_id: str
    ) -> RunView:
        texts: list[str] = []
        paused = False
        events: list[Any] = []
        async with self._lock(session_id):
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=message,
            ):
                events.append(event)
                if getattr(event, "long_running_tool_ids", None):
                    paused = True
                for part in getattr(getattr(event, "content", None), "parts", None) or []:
                    if getattr(part, "text", None) and getattr(event, "author", None) != "user":
                        texts.append(part.text)
        reply = "\n".join(texts).strip() or None
        if paused and self.suppress_text_when_paused:
            # Do not send leftover prose when asking for a choice
            reply = None
        elif reply:
            await self.channel.send_text(session_id, reply)
        return RunView(reply_text=reply, paused=paused, events=events)
