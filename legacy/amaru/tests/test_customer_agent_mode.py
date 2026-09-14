"""Amaru root orchestrator and customer sub-agent wiring."""

from google.adk.planners import BuiltInPlanner

from app.agent import HANDOFF_SOURCE, root_agent
from app.subagents.bridge.agent import bridge_agent
from app.subagents.customer.agent import customer_agent
from app.subagents.customer.tools.search_context import _ORG_SLUG
from app.subagents.qualifier.agent import qualifier_agent


def test_root_agent_name_is_amaru() -> None:
    assert root_agent.name == "amaru"


def test_customer_agent_uses_chat_mode_with_history() -> None:
    assert customer_agent.mode == "chat"
    assert customer_agent.include_contents == "default"
    assert customer_agent.before_model_callback is not None


def test_knowledge_search_org_slug_is_amaru() -> None:
    assert _ORG_SLUG == "amaru"


def test_handoff_source_is_amaru_tools() -> None:
    assert HANDOFF_SOURCE == "amaru_tools"


def test_orchestrator_has_qualifier_bridge_activate_and_customer_subagents() -> None:
    names = {agent.name for agent in root_agent.sub_agents}
    assert names == {"qualifier", "bridge", "activate", "customer"}


def test_customer_agent_has_search_and_reply_tools() -> None:
    flat: list[str] = []
    for tool in customer_agent.tools:
        name = getattr(tool, "name", None)
        if name:
            flat.append(name)
        elif callable(tool):
            flat.append(tool.__name__)
        else:
            flat.append(type(tool).__name__)
    assert "search_context" in flat
    assert "reply_with_text" in flat
    assert "submit_lead_qualification" not in flat
    assert "request_human_handoff" not in flat


def test_qualifier_has_no_tools_and_output_schema() -> None:
    assert qualifier_agent.tools == []
    assert qualifier_agent.output_key == "bant_result"
    assert qualifier_agent.output_schema is not None


def test_bridge_agent_has_no_tools() -> None:
    assert bridge_agent.tools == []
    assert bridge_agent.name == "bridge"


def test_customer_thinking_budget_is_1024_and_thoughts_hidden() -> None:
    planner = customer_agent.planner
    assert isinstance(planner, BuiltInPlanner)
    thinking = planner.thinking_config
    assert thinking.thinking_budget == 1024
    assert thinking.include_thoughts is False
