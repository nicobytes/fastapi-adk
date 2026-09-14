# Be Unique agent (BaseAgent orchestrator + sub-agents)

Standalone [agents-cli](https://google.github.io/agents-cli/) project for Be Unique WhatsApp (Sofía + agenda + HITL explícito).

## Layout

```
app/
├── agent.py                 # root_agent = BeUniqueOrchestrator + App
├── orchestrator.py          # qualifier → Python score/handoff → bridge | customer
├── qualification.py         # apply_bant_signals / maybe_execute_handoff
├── callbacks.py             # seed_session_state (turn counter) + recover_unknown_tool_error
├── subagents/
│   ├── qualifier/           # silent BANT classifier (output_schema, no tools)
│   │   ├── agent.py
│   │   └── instructions/
│   ├── bridge/              # handoff closing message (flash-lite, no tools)
│   │   ├── agent.py
│   │   └── instructions/
│   ├── activate/            # inactivity nudge (flash-lite, no tools)
│   │   ├── agent.py
│   │   └── instructions/
│   └── customer/            # Sofía chat (skills + agenda + reply_with_*)
│       ├── agent.py
│       ├── instructions/
│       ├── skills/          # customer ADK skills (ENABLED_SKILLS)
│       └── tools/
└── fast_api_app.py
```

Shared libs via `chatty-agent-common` (vendored wheel): lead scoring, handoff, instructions loader, providers, scheduling, skills loader.

## Tenant IDs

- ADK root `name`: `be_unique`
- Customer sub-agent `name`: `customer`
- Qualifier sub-agent `name`: `qualifier` (internal; not a Nest contract)
- Bridge sub-agent `name`: `bridge` (internal; handoff turns only)
- Activate sub-agent `name`: `activate` (internal; Nest scheduler nudge only)
- Scheduling slug: `_ORG_SLUG = "be-unique"`
- Handoff `source`: `be-unique_tools`

## Architecture

**BaseAgent orchestrator** (not ADK Workflow):

1. Each turn: run `qualifier` (flash-lite, `output_schema`, no tools) — events are **not** yielded to Nest.
2. Python (`qualification.py`) scores BANT, persists snapshot, calls `execute_conversation_handoff` **only** when `explicit_human_request` is true (score / plan+date **never** authorize handoff).
3. On handoff: run `bridge` (flash-lite, no tools) for a **personalized** closing message using `handoff_bridge_example` as tone guide (CRM → env → default). Fallback to deterministic bridge if bridge agent fails. **Do not** run `customer`.
4. On Nest activate (`activate_pending` in session state): run `activate` (flash-lite, no tools) for a short inactivity nudge. **Do not** run qualifier, bridge, or customer; **do not** bump `user_turn_count`.
5. Otherwise: yield `customer` events (flash-latest, Sofía + skills + agenda + `reply_with_*`).
6. Nest sends the last visible model text to WhatsApp — **no BANT JSON filtering** in the API parser.

## Agent invariants

1. **BANT is not a tool** — Qualifier uses `output_key="bant_result"`; scoring/handoff stay in Python. Each qualify turn persists the latest BANT snapshot to `conversations.metadata.qualification`; not exposed on WhatsApp/SSE.
2. **Handoff explícito only** — `allow_score_handoff=False`; `plan_and_date_confirmed` is tracked but does not fast-track handoff.
3. **Turn gate** — `seed_session_state` increments `user_turn_count`; handoff blocked on turn 1 unless `explicit_human_request`.
4. **No BANT in SSE** — Orchestrator never yields qualifier output; customer instructions tell the model to ignore internal JSON in history.
5. **Agent-spoken bridge** — After Python handoff, bridge sub-agent composes one short WhatsApp message (example-guided, may mention sede/tratamiento/fecha). No payment/reservation URLs.
6. **Activate path** — When `activate_pending=true`, only the activate sub-agent runs; no BANT, no turn-gate bump.
7. **Skills, not RAG** — Customer uses `FilteredSkillToolset` (`list_skills`, `load_skill`, `load_skill_resource`) + `on_tool_error_callback=recover_unknown_tool_error`. There is no `search_context`. Hard cutover: leftover files in CRM Archivos are ignored after deploy (Archivos UI follow-up is out of scope).

## Local / tests / evals

```bash
just sync && just serve
uv run python -m pytest tests/ -q
```

`ADK_DEV_MODE=true` (via `just serve` / `just serve-prod`):

- Ensures a local Supabase `conversations` row with `id = ADK session.id` (plus a playground customer on the org WhatsApp inbox) so `book_appointment` / handoff / score hit real rows. Requires `SUPABASE_URL` on localhost and a seeded DB (`just db-reset` in `projects/supabase`). Optional `ADK_DEV_INBOX_ID` if the org has multiple WhatsApp inboxes.
- `book_appointment` only sends `conversationId` after that ensure succeeds. With `just serve-prod` (cloud Supabase) ensure is skipped, so booking omits `conversationId` and still works against Nest without a CRM row. Use `just serve` + local Nest/Supabase for CRM-linked bookings.
- Skips handoff/score updates only when that ensure failed and the row is still missing.
- Mirrors `reply_with_*` intent bodies as an extra model text event so the playground shows a chat bubble. Nest still prefers intents, so WhatsApp is not duplicated.

For booking tools, also run Nest locally with matching `CHATTY_API_URL` / `API_WEBHOOK_SECRET`.

## Manual check

1. Turn 1: saludo + sede; no handoff aunque pida cita. No skills on the greeting turn.
2. Turn 2+: pide humano explícito → solo bridge; no BANT JSON visible.
3. Score alto / cita confirmada sin pedir humano → Sofía continúa (agenda/skills).
4. Activate pending → nudge corto; no qualifier ni customer.
