from __future__ import annotations

from typing import TYPE_CHECKING, override

from google.adk.tools import skill_toolset

if TYPE_CHECKING:
    from google.adk.models.llm_request import LlmRequest
    from google.adk.tools.tool_context import ToolContext

_ALLOWED_SKILL_TOOLS = ["list_skills", "load_skill"]


def build_filtered_skill_instruction(
    allowed_tools: list[str],
    *,
    prefix: str | None = None,
) -> str:
    """System instruction that only mentions tools present in tool_filter.

    Upstream SkillToolset always injects run_skill_script / load_skill_resource
    even when those tools are filtered out, which causes the model to hallucinate
    them and ADK to raise ValueError (still present in 2.6.2; see
    https://github.com/google/adk-python/issues/6448).
    """
    p = f"{prefix}_" if prefix else ""
    allowed = set(allowed_tools)
    lines = [
        "You can use specialized 'skills' to help you with complex tasks.",
        "You MUST use the skill tools to interact with these skills.",
        "",
        "Skills are folders of instructions that extend your capabilities.",
        "Each skill folder contains a SKILL.md with metadata and markdown "
        "instructions.",
        "",
        "This is very important:",
        "",
    ]
    step = 1
    if "list_skills" in allowed:
        lines.append(
            f"{step}. Use `{p}list_skills` to discover available skills and "
            "their descriptions."
        )
        step += 1
    if "load_skill" in allowed:
        lines.append(
            f"{step}. If a skill seems relevant to the current user query, you "
            f'MUST use the `{p}load_skill` tool with `skill_name="<SKILL_NAME>"` '
            "to read its full instructions before proceeding."
        )
        step += 1
        lines.append(
            f"{step}. Once you have read the instructions, follow them exactly "
            "as documented before replying to the user."
        )
        step += 1
        lines.append(
            f"{step}. Loading a skill only retrieves its instructions; it does "
            f"NOT complete your turn. After a `{p}load_skill` call returns, "
            "continue in the SAME turn: apply the skill rules, then write your "
            "reply as normal model text. Never end your turn with an empty "
            "response right after loading a skill."
        )
        step += 1
    if "load_skill_resource" in allowed:
        lines.append(
            f"{step}. Use `{p}load_skill_resource` with the relative path "
            "(e.g. `references/tarifario.md`) if the skill lists reference files, "
            "to load only the L3 files you need before answering with prices, "
            "durations, or clinical detail."
        )
        step += 1

    lines.extend(["", "Hard constraints for the currently configured skills:"])
    if "run_skill_script" not in allowed and "load_skill_resource" not in allowed:
        lines.append(
            f"- Do NOT call `{p}run_skill_script` or `{p}load_skill_resource` — "
            "those tools are not available. The skills only contain SKILL.md "
            "instructions (no scripts/ or references/)."
        )
    else:
        if "run_skill_script" not in allowed:
            lines.append(
                f"- Do NOT call `{p}run_skill_script` — that tool is not "
                "available. There are no skill scripts."
            )
        if "load_skill_resource" not in allowed:
            lines.append(
                f"- Do NOT call `{p}load_skill_resource` — that tool is not "
                "available. The skills only contain SKILL.md instructions "
                "(no scripts/ or references/)."
            )
    lines.append(
        "- Never wrap your user-facing reply inside a tool call. After "
        "loading a skill, emit the final WhatsApp message as normal model "
        "text and end the turn."
    )
    return "\n".join(lines)


class FilteredSkillToolset(skill_toolset.SkillToolset):
    """SkillToolset whose system instruction matches the tool_filter."""

    @override
    async def process_llm_request(
        self, *, tool_context: ToolContext, llm_request: LlmRequest
    ) -> None:
        allowed = (
            list(self.tool_filter)
            if isinstance(self.tool_filter, list)
            else list(_ALLOWED_SKILL_TOOLS)
        )
        llm_request.append_instructions(
            [
                build_filtered_skill_instruction(
                    allowed,
                    prefix=self.tool_name_prefix,
                )
            ]
        )
