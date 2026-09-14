# chatty-agent-common

Shared helpers for Chatty Python agents (handoff, BANT scoring, Supabase/Gemini/
Chatty API providers, FilteredSkillToolset / skills loader, knowledge search,
scheduling, outbound intent tools). WhatsApp wire formatting and Meta Graph
calls live in NestJS; agent prompts carry native syntax rules. Outbound tools
only emit validated intents.

**Not published to PyPI.** Tenant agents consume it as a **local wheel** after
`just vendor-common` runs `uv build --wheel` and copies the artifact into
`vendor/chatty_agent_common-*-py3-none-any.whl`.

See [projects/agents/AGENTS.md](../AGENTS.md) for packaging and tenant conventions.

## Develop

```bash
cd projects/agents/chatty-agent-common
uv sync
uv run python -m pytest
```

After changing this package, rebuild into each agent:

```bash
cd projects/agents/amaru && just sync
cd projects/agents/be-unique && just sync
```

Installs are not editable — always re-vendor. Package `version` stays at
`0.0.0` so agent `[tool.uv.sources]` paths never need updating; git is the
source of truth for shared code.

## Public API

```python
from chatty_agent_common.handoff import (
    execute_conversation_handoff,
    persist_conversation_qualification_snapshot,
)
from chatty_agent_common.lead_scoring import calculate_lead_score, HANDOFF_THRESHOLD
from chatty_agent_common.qualification import (
    QualificationPolicy,
    apply_bant_signals,
    maybe_execute_handoff,
    parse_bant_signals,
)
from chatty_agent_common.providers.supabase import get_supabase_client, search_knowledge
from chatty_agent_common.providers.gemini import get_embedding

# Keep FilteredSkillToolset until adk-python#6448 lands (open as of ADK 2.6.2)
from chatty_agent_common.skills_toolset import FilteredSkillToolset
from chatty_agent_common.skills_loader import load_skills_by_name, shared_skills_dir
from chatty_agent_common.knowledge_search import run_knowledge_search
from chatty_agent_common.scheduling import (
    run_book_appointment,
    run_list_available_days,
    run_list_available_hours,
)
from chatty_agent_common.outbound import get_outbound_intent_tools
```

Pass tenant `organization_slug` into `run_knowledge_search` /
`run_list_available_days` / `run_list_available_hours` / `run_book_appointment`
(never hardcoded here).

Each qualify turn writes the latest BANT snapshot to
`conversations.metadata.qualification` (signals + derived score) via the
`patch_conversation_agent_state` RPC (`metadata || patch`). Handoff patches
`metadata.handoff` the same way so concurrent writes cannot erase each other.
Scheduling takes platform `schedule_slug` plus optional `duration_minutes`
(from RAG) and `service_name` on book; tenants map domain labels (e.g. sedes)
in thin wrappers.

Register outbound tools explicitly:

```python
from chatty_agent_common.outbound import (
    capture_outbound_for_playground,
    get_outbound_intent_tools,
    mirror_outbound_for_playground,
)

tools = [
    search_context,
    *get_outbound_intent_tools(),
    # or: *get_outbound_intent_tools(enabled={"reply_with_text", "send_template"}),
]
# With ADK_DEV_MODE=true, playground shows intent body as a chat bubble too:
# after_tool_callback=[
#     stop_turn_after_outbound_intent,  # end turn after reply_with_*
#     capture_outbound_for_playground,
# ],
# after_agent_callback=mirror_outbound_for_playground,

# Also ensure conversations.id = session.id in local Supabase:
# from chatty_agent_common.playground_session import (
#     make_ensure_playground_conversation_callback,
# )
# before_agent_callback=[
#     make_ensure_playground_conversation_callback("be-unique"),
#     seed_session_state,
# ],
```

Do not put Meta tokens or `graph.facebook.com` usage in agents.
