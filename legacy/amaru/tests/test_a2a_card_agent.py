"""A2A card stub must not read .model/.tools from BaseAgent orchestrator."""

from google.adk.agents.llm_agent import Agent

from app.agent import CARD_INSTRUCTION, root_agent
from app.subagents.customer.agent import customer_agent


def test_a2a_card_agent_builds_from_customer_llm_fields() -> None:
    """Regression: lifespan used root_agent.model and crashed on AmaruOrchestrator."""
    assert not hasattr(root_agent, "model")
    assert not hasattr(root_agent, "tools")

    card_agent = Agent(
        model=customer_agent.model,
        name=root_agent.name,
        description=root_agent.description,
        instruction=CARD_INSTRUCTION,
        tools=customer_agent.tools,
    )

    assert card_agent.name == "amaru"
    assert card_agent.model == customer_agent.model
    assert card_agent.tools == customer_agent.tools
