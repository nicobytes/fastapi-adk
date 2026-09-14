"""FilteredSkillToolset must not advertise filtered-out skill tools."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

from google.adk.models.llm_request import LlmRequest

from chatty_agent_common.skills_loader import load_skills_by_name
from chatty_agent_common.skills_toolset import (
    FilteredSkillToolset,
    build_filtered_skill_instruction,
)


def _write_skill(root: Path, name: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: fixture\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def test_filtered_instruction_omits_script_and_resource_tools() -> None:
    text = build_filtered_skill_instruction(["list_skills", "load_skill"])
    assert "list_skills" in text
    assert "load_skill" in text
    # Explicit ban is allowed; positive usage instructions are not.
    assert "Use `run_skill_script`" not in text
    assert "use `run_skill_script`" not in text
    assert "Use `load_skill_resource`" not in text
    assert "use `load_skill_resource`" not in text
    assert "Do NOT call `run_skill_script`" in text
    assert "Do NOT call `load_skill_resource`" in text or (
        "or `load_skill_resource`" in text
    )
    assert "normal model text" in text


def test_filtered_instruction_includes_load_skill_resource_when_allowed() -> None:
    text = build_filtered_skill_instruction(
        ["list_skills", "load_skill", "load_skill_resource"]
    )
    assert "Use `load_skill_resource`" in text
    assert "references/tarifario.md" in text
    assert "Do NOT call `load_skill_resource`" not in text
    assert "no hay references/" not in text
    assert "no scripts/ or references/" not in text
    assert "Do NOT call `run_skill_script`" in text


def test_filtered_instruction_mentions_only_allowed_tools_positively() -> None:
    text = build_filtered_skill_instruction(["list_skills"])
    assert "`list_skills`" in text
    assert "`load_skill`" not in text or "Do NOT" in text
    assert "Use `load_skill`" not in text


def test_process_llm_request_injects_filtered_instruction(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    skills = load_skills_by_name(
        ["demo-skill"],
        search_dirs=[tmp_path],
    )
    toolset = FilteredSkillToolset(
        skills=skills,
        tool_filter=["list_skills", "load_skill"],
    )
    request = LlmRequest()
    tool_context = MagicMock()

    asyncio.run(
        toolset.process_llm_request(
            tool_context=tool_context,
            llm_request=request,
        )
    )

    system = request.config.system_instruction or ""
    if not isinstance(system, str):
        system = str(system)
    assert "list_skills" in system
    assert "load_skill" in system
    assert "Use `run_skill_script`" not in system
    assert "use `run_skill_script`" not in system
    assert isinstance(toolset, FilteredSkillToolset)
