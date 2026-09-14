"""Unknown-tool recovery for the Amaru customer agent."""

from unittest.mock import MagicMock

from google.adk.tools.base_tool import BaseTool

from app.agent import recover_unknown_tool_error
from app.subagents.customer.agent import customer_agent


def test_recover_unknown_tool_error_returns_recovery_dict() -> None:
    tool = BaseTool(name="run_skill_script", description="missing")
    result = recover_unknown_tool_error(
        tool,
        {},
        MagicMock(),
        ValueError("Tool 'run_skill_script' not found."),
    )
    assert result["error_code"] == "TOOL_NOT_FOUND"
    assert "run_skill_script" in result["error"]
    assert "directamente como texto" in result["error"]


def test_recover_unknown_tool_error_surfaces_execution_failures() -> None:
    tool = BaseTool(name="search_context", description="ok")
    result = recover_unknown_tool_error(
        tool,
        {},
        MagicMock(),
        RuntimeError("search-knowledge timed out; try again or narrow the query."),
    )
    assert result["error_code"] == "TOOL_ERROR"
    assert "search_context" in result["error"]
    assert "timed out" in result["error"]


def test_customer_agent_registers_tool_error_callback() -> None:
    assert customer_agent.on_tool_error_callback is recover_unknown_tool_error


def test_customer_agent_has_no_skill_toolset() -> None:
    tool_names = [getattr(t, "name", type(t).__name__) for t in customer_agent.tools]
    assert "FilteredSkillToolset" not in tool_names
    assert all(
        getattr(t, "__class__", type(t)).__name__ != "FilteredSkillToolset"
        for t in customer_agent.tools
    )
