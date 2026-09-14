"""Handoff bridge sub-agent: personalized closing message after Python HITL."""

from __future__ import annotations

from google.adk.agents import Agent
from google.genai import types

from app.subagents.bridge.instructions import STATIC_INSTRUCTION, build_instruction
from chatty_agent_common.llm_contents import strip_internal_bant_contents

bridge_agent = Agent(
    name="bridge",
    model="gemini-flash-lite-latest",
    description="Be Unique handoff bridge message composer (post-Python HITL).",
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
