"""Customer-facing Amaru chat sub-agent."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from app.callbacks import recover_unknown_tool_error
from app.subagents.customer.instructions import STATIC_INSTRUCTION, build_instruction
from app.subagents.customer.tools.search_context import search_context
from chatty_agent_common.llm_contents import strip_internal_bant_contents
from chatty_agent_common.outbound import (
    capture_outbound_for_playground,
    clear_outbound_preview_if_model_text,
    get_outbound_intent_tools,
    stop_turn_after_outbound_intent,
)

customer_agent = Agent(
    name="customer",
    model="gemini-flash-latest",
    description="Amaru customer support agent for Xperiencia travel.",
    mode="chat",
    include_contents="default",
    static_instruction=STATIC_INSTRUCTION,
    instruction=build_instruction,
    tools=[
        search_context,
        *get_outbound_intent_tools(enabled={"reply_with_text"}),
    ],
    before_model_callback=strip_internal_bant_contents,
    after_model_callback=clear_outbound_preview_if_model_text,
    after_tool_callback=[
        stop_turn_after_outbound_intent,
        capture_outbound_for_playground,
    ],
    on_tool_error_callback=recover_unknown_tool_error,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,
            thinking_budget=1024,
        )
    ),
)
