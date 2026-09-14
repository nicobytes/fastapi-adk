"""Customer-facing Sofía chat sub-agent."""

from __future__ import annotations

from pathlib import Path

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from app.callbacks import recover_unknown_tool_error
from app.subagents.customer.instructions import STATIC_INSTRUCTION, build_instruction
from app.subagents.customer.tools.scheduling import (
    book_appointment,
    cancel_appointment,
    list_available_days,
    list_available_hours,
    list_my_appointments,
    reschedule_appointment,
)
from app.subagents.customer.tools.sede_location import send_sede_location
from chatty_agent_common.llm_contents import strip_internal_bant_contents
from chatty_agent_common.outbound import (
    capture_outbound_for_playground,
    clear_outbound_preview_if_model_text,
    get_outbound_intent_tools,
    stop_turn_after_outbound_intent,
)
from chatty_agent_common.skills_loader import load_skills_by_name
from chatty_agent_common.skills_toolset import FilteredSkillToolset

ENABLED_SKILLS = [
    "info-institucional",
    "depilacion-laser",
    "faciales",
    "promociones",
    "derivacion-equipo",
]
_SKILLS_DIR = Path(__file__).resolve().parent / "skills"

customer_agent = Agent(
    name="customer",
    model="gemini-flash-latest",
    description="Sofía — Be Unique Clínica Estética customer support agent.",
    mode="chat",
    include_contents="default",
    static_instruction=STATIC_INSTRUCTION,
    instruction=build_instruction,
    tools=[
        FilteredSkillToolset(
            skills=load_skills_by_name(ENABLED_SKILLS, search_dirs=[_SKILLS_DIR]),
            tool_filter=["list_skills", "load_skill", "load_skill_resource"],
        ),
        list_my_appointments,
        list_available_days,
        list_available_hours,
        book_appointment,
        reschedule_appointment,
        cancel_appointment,
        send_sede_location,
        *get_outbound_intent_tools(
            enabled={"reply_with_text", "reply_with_buttons", "reply_with_list"}
        ),
    ],
    before_model_callback=strip_internal_bant_contents,
    after_model_callback=clear_outbound_preview_if_model_text,
    after_tool_callback=[
        stop_turn_after_outbound_intent,
        capture_outbound_for_playground,
    ],
    on_tool_error_callback=recover_unknown_tool_error,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,
            thinking_budget=1024,
        )
    ),
)
