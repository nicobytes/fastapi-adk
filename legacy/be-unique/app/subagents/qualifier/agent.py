"""Silent BANT classifier sub-agent for Be Unique."""

from __future__ import annotations

from pathlib import Path

from google.adk.agents import Agent
from google.genai import types
from pydantic import BaseModel, Field

from chatty_agent_common.instructions import load_agent_instructions
from chatty_agent_common.lead_scoring import (
    BudgetStatus,
    InterestLevel,
    PurchaseUrgency,
)

_INSTRUCTIONS_DIR = Path(__file__).resolve().parent / "instructions"
_instruction_bundle = load_agent_instructions(_INSTRUCTIONS_DIR)


class BantSignals(BaseModel):
    """Structured BANT output consumed by the Be Unique orchestrator."""

    interest_level: InterestLevel = Field(
        description="Lead interest: Low, Medium, or High.",
    )
    budget_status: BudgetStatus = Field(
        description="Budget alignment: NotMentioned, Insufficient, or Aligned.",
    )
    purchase_urgency: PurchaseUrgency = Field(
        description="Purchase urgency: Immediate, ShortTerm, LongTerm, or Uncertain.",
    )
    has_decision_authority: bool = Field(
        description="True when the user can decide or book for themselves.",
    )
    explicit_human_request: bool = Field(
        description="True when the user explicitly asks for a human advisor.",
    )
    plan_and_date_confirmed: bool = Field(
        description=(
            "True when a concrete service/treatment and near-term appointment "
            "date/window are confirmed."
        ),
    )


qualifier_agent = Agent(
    name="qualifier",
    model="gemini-flash-lite-latest",
    description="Silent BANT signal extractor for Be Unique.",
    static_instruction=_instruction_bundle.static_instruction,
    instruction=_instruction_bundle.build_instruction,
    output_schema=BantSignals,
    output_key="bant_result",
    generate_content_config=types.GenerateContentConfig(temperature=0),
)
