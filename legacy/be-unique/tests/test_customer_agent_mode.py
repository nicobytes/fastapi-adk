"""Be Unique root orchestrator and Sofía customer sub-agent wiring."""

from app.agent import HANDOFF_SOURCE, root_agent
from app.subagents.activate.agent import activate_agent
from app.subagents.bridge.agent import bridge_agent
from app.subagents.customer.agent import ENABLED_SKILLS, customer_agent
from app.subagents.customer.tools.scheduling import _ORG_SLUG
from app.subagents.qualifier.agent import qualifier_agent
from chatty_agent_common.skills_toolset import FilteredSkillToolset

_SKILL_TOOL_NAMES = ("list_skills", "load_skill", "load_skill_resource")


def _tool_labels(agent) -> list[str]:
    flat: list[str] = []
    for tool in agent.tools:
        name = getattr(tool, "name", None)
        if name:
            flat.append(name)
        elif callable(tool):
            flat.append(tool.__name__)
        else:
            flat.append(type(tool).__name__)
    return flat


def test_root_agent_name_is_be_unique() -> None:
    assert root_agent.name == "be_unique"


def test_customer_agent_uses_chat_mode_with_history() -> None:
    assert customer_agent.mode == "chat"
    assert customer_agent.include_contents == "default"


def test_knowledge_search_org_slug_is_be_unique() -> None:
    assert _ORG_SLUG == "be-unique"


def test_handoff_source_is_be_unique_tools() -> None:
    assert HANDOFF_SOURCE == "be-unique_tools"


def test_orchestrator_has_qualifier_bridge_activate_and_customer_subagents() -> None:
    names = {agent.name for agent in root_agent.sub_agents}
    assert names == {"qualifier", "bridge", "activate", "customer"}


def test_root_agent_has_no_skill_toolset() -> None:
    tools = getattr(root_agent, "tools", None) or []
    assert not any(
        getattr(t, "__class__", type(t)).__name__ == "FilteredSkillToolset"
        for t in tools
    )


def test_customer_agent_has_skills_scheduling_and_reply_tools() -> None:
    flat = _tool_labels(customer_agent)
    assert "search_context" not in flat
    assert "FilteredSkillToolset" in flat
    assert any(isinstance(t, FilteredSkillToolset) for t in customer_agent.tools)
    assert "list_available_days" in flat
    assert "list_available_hours" in flat
    assert "book_appointment" in flat
    assert "reply_with_buttons" in flat
    assert "reply_with_text" in flat
    assert "reply_with_list" in flat
    assert "send_sede_location" in flat
    assert "reply_with_location" not in flat
    assert "submit_lead_qualification" not in flat
    assert "request_human_handoff" not in flat
    skillset = next(
        t for t in customer_agent.tools if isinstance(t, FilteredSkillToolset)
    )
    assert list(skillset.tool_filter) == list(_SKILL_TOOL_NAMES)
    assert ENABLED_SKILLS == [
        "info-institucional",
        "depilacion-laser",
        "faciales",
        "promociones",
        "derivacion-equipo",
    ]


def test_qualifier_has_no_tools_and_output_schema() -> None:
    assert qualifier_agent.tools == []
    assert qualifier_agent.output_key == "bant_result"
    assert qualifier_agent.output_schema is not None


def test_bridge_agent_has_no_tools() -> None:
    assert bridge_agent.tools == []
    assert bridge_agent.name == "bridge"


def test_qualifier_bridge_activate_have_no_skill_or_search_tools() -> None:
    for agent in (qualifier_agent, bridge_agent, activate_agent):
        assert agent.tools == []
        text = str(agent.static_instruction or "")
        assert "search_context" not in text
        for name in _SKILL_TOOL_NAMES:
            assert name not in text
