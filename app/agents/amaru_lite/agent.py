from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.base_tool import BaseTool


def create_amaru_lite_agent(*, tools: list[BaseTool], model: str = "gemini-2.5-flash") -> LlmAgent:
    """Optional lightweight routing brain (P3 lab)."""
    return LlmAgent(
        name="amaru_lite",
        model=model,
        instruction=(
            "You are a lightweight routing assistant. Be brief. "
            "If the customer asks for a human advisor, say you will connect them "
            "and stop. Otherwise help briefly. Use ask_choice when offering options."
        ),
        tools=tools,
    )
