"""Allow agents-cli eval generate with ADK dynamic instruction providers.

Vertex ``AgentConfig.from_agent`` requires ``instruction: str``, but Amaru
uses ``build_instruction`` (callable). The config is metadata-only; the live
agent still receives the callable. Coerce callables to a placeholder string.
"""

from __future__ import annotations


def _patch_agent_config() -> None:
    try:
        from vertexai._genai.types.evals import AgentConfig
    except ImportError:
        return

    _orig = AgentConfig.from_agent.__func__  # type: ignore[attr-defined]

    @classmethod  # type: ignore[misc]
    def from_agent(cls, agent):
        instruction = getattr(agent, "instruction", None)
        if callable(instruction):
            placeholder = getattr(instruction, "__name__", "dynamic_instruction")
            # Temporarily replace so the original validator accepts it.
            try:
                object.__setattr__(agent, "instruction", placeholder)
            except Exception:
                agent.instruction = placeholder  # type: ignore[attr-defined]
            try:
                return _orig(cls, agent)
            finally:
                try:
                    object.__setattr__(agent, "instruction", instruction)
                except Exception:
                    agent.instruction = instruction  # type: ignore[attr-defined]
        return _orig(cls, agent)

    AgentConfig.from_agent = from_agent  # type: ignore[method-assign]


_patch_agent_config()
