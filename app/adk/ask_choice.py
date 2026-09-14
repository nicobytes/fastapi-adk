from __future__ import annotations

from typing import Any

from google.adk.tools import LongRunningFunctionTool, ToolContext

from app.channel.service import ChannelService
from app.conversations.store import ConversationStore
from app.conversations.types import ChoiceOption


def create_ask_choice_tool(
    channel: ChannelService, store: ConversationStore
) -> LongRunningFunctionTool:
    async def ask_choice(
        prompt: str,
        options: list[dict[str, str]],
        tool_context: ToolContext,
    ) -> None:
        """Show choice buttons and pause until the user clicks one. Call once, then stop."""
        session_id = tool_context.session.id
        function_call_id = tool_context.function_call_id or "unknown"
        newly = await store.mark_tool_sent(function_call_id, session_id, "ask_choice")
        tool_context.actions.skip_summarization = True
        if not newly:
            return None
        normalized = [ChoiceOption(id=str(o["id"]), title=str(o["title"])) for o in options]
        await channel.send_buttons(
            session_id,
            prompt,
            normalized,
            function_call_id=function_call_id,
            invocation_id=tool_context.invocation_id,
        )
        return None

    return LongRunningFunctionTool(func=ask_choice)
