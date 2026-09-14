"""Activate sub-agent: short inactivity nudge after Nest scheduler."""

from __future__ import annotations

from google.adk.agents import Agent
from google.genai import types

from app.subagents.activate.instructions import STATIC_INSTRUCTION, build_instruction
from chatty_agent_common.llm_contents import strip_internal_bant_contents

activate_agent = Agent(
    name="activate",
    model="gemini-flash-lite-latest",
    description="Be Unique inactivity nudge composer (Nest activate path).",
    mode="chat",
    include_contents="default",
    static_instruction=STATIC_INSTRUCTION,
    instruction=build_instruction,
    before_model_callback=strip_internal_bant_contents,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        max_output_tokens=120,
    ),
)
