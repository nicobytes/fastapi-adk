from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.agents.llm_agent import ToolUnion

from app.constants import DEFAULT_AGENT_ID


def create_default_agent(*, tools: list[ToolUnion], model: str = "gemini-2.5-flash") -> LlmAgent:
    return LlmAgent(
        name=DEFAULT_AGENT_ID,
        model=model,
        instruction=(
            "You are a helpful POC assistant for messaging. "
            "When you need the user to pick among options, call ask_choice once with a prompt "
            "and at least two options (id + title), then stop. Do not invent the choice. "
            "Keep replies short."
        ),
        tools=tools,
    )
