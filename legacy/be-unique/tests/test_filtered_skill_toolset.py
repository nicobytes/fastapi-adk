"""Unknown-tool recovery for the Be Unique customer agent."""

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
    tool = BaseTool(name="reply_with_buttons", description="ok")
    result = recover_unknown_tool_error(
        tool,
        {},
        MagicMock(),
        ValueError("1 validation error for ReplyButton"),
    )
    assert result["error_code"] == "TOOL_ERROR"
    assert "reply_with_buttons" in result["error"]
    assert "validation error" in result["error"]


def test_customer_agent_registers_tool_error_callback() -> None:
    assert customer_agent.on_tool_error_callback is recover_unknown_tool_error


def test_customer_agent_has_filtered_skill_toolset() -> None:
    assert any(
        getattr(t, "__class__", type(t)).__name__ == "FilteredSkillToolset"
        for t in customer_agent.tools
    )
    assert customer_agent.on_tool_error_callback is recover_unknown_tool_error
