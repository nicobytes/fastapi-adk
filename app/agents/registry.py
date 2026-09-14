from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.agents.llm_agent import ToolUnion

from app.agents.default import create_default_agent
from app.constants import DEFAULT_AGENT_ID


def get_agent(agent_id: str | None, *, tools: list[ToolUnion]) -> LlmAgent:
    if agent_id in (None, "", DEFAULT_AGENT_ID, "amaru"):
        return create_default_agent(tools=tools)
    if agent_id == "amaru_lite":
        from app.agents.amaru_lite.agent import create_amaru_lite_agent

        return create_amaru_lite_agent(tools=tools)
    return create_default_agent(tools=tools)
