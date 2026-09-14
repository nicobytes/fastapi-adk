# Amaru agent (BaseAgent orchestrator + sub-agents)

Standalone [agents-cli](https://google.github.io/agents-cli/) project for Xperiencia WhatsApp (BANT qualification + HITL handoff).

## Layout

```
app/
├── agent.py                 # root_agent = AmaruOrchestrator + App
├── orchestrator.py          # qualifier → Python score/handoff → bridge | customer
├── qualification.py         # apply_bant_signals / maybe_execute_handoff
├── callbacks.py             # seed_session_state (turn counter)
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
│   └── customer/            # chat agent (search_context + reply_with_text)
│       ├── agent.py
│       ├── instructions/
│       └── tools/
├── skills/                  # optional tenant skill overrides (future)
└── fast_api_app.py
```

Shared libs via `chatty-agent-common` (vendored wheel): lead scoring, handoff, instructions loader, providers, skills loader.

## Tenant IDs

- ADK root `name`: `amaru`
- Customer sub-agent `name`: `customer`
- Qualifier sub-agent `name`: `qualifier` (internal; not a Nest contract)
- Bridge sub-agent `name`: `bridge` (internal; handoff turns only)
- Activate sub-agent `name`: `activate` (internal; Nest scheduler nudge only)
- Knowledge slug: `_ORG_SLUG = "amaru"`
- Handoff `source`: `amaru_tools`

## Architecture

**BaseAgent orchestrator** (not ADK Workflow):

1. Each turn: run `qualifier` (flash-lite, `output_schema`, no tools) — events are **not** yielded to Nest.
2. Python (`qualification.py`) scores BANT, applies turn gate, calls `execute_conversation_handoff` when qualified.
3. On handoff: run `bridge` (flash-lite, no tools) for a **personalized** closing message using `handoff_bridge_example` as tone guide (CRM → env → default). Fallback to deterministic bridge if bridge agent fails. **Do not** run `customer`.
4. On Nest activate (`activate_pending` in session state): run `activate` (flash-lite, no tools) for a short inactivity nudge. **Do not** run qualifier, bridge, or customer; **do not** bump `user_turn_count`.
5. Otherwise: yield `customer` events (flash-latest, `search_context` + `reply_with_text`).
6. Nest sends the last visible model text to WhatsApp — **no BANT JSON filtering** in the API parser.

## Agent invariants

1. **BANT is not a tool** — Qualifier uses `output_key="bant_result"`; scoring/handoff stay in Python. Each qualify turn persists the latest BANT snapshot to `conversations.metadata.qualification` (signals + score + qualifies + `updated_at`); not exposed on WhatsApp/SSE. Amaru `qualifies` is the four-path gate, not score ≥ 70.
2. **Turn gate** — `seed_session_state` increments `user_turn_count`; handoff blocked on turn 1 unless `explicit_human_request` or `disability_access_inquiry`.
3. **No BANT in SSE** — Orchestrator never yields qualifier output; customer instructions tell the model to ignore internal JSON in history.
4. **Agent-spoken bridge** — After Python handoff, bridge sub-agent composes one short WhatsApp message (example-guided, may mention plan/date). No payment/reservation URLs.
5. **Activate path** — When `activate_pending=true`, only the activate sub-agent runs; no BANT, no turn-gate bump.
6. **Four handoff paths only** — (1) published plan + listed departure + accept booking that outing; (2) explicit human request; (3) accept custom group/date after Amaru offered it; (4) disability/accessibility question. Score ≥ 70, date mention, list pick, and early “quiero reservar” do **not** hand off. Operator reason is one of the four canonical strings — never `Lead calificado para atención humana.` on success.
7. **Skills (when added)** — Use `FilteredSkillToolset` + `on_tool_error_callback=recover_unknown_tool_error`.

## Local dev

```bash
cd projects/supabase && just db-reset    # seed.sql + amaru-kb.sql (RAG fixture)
just fn-serve                          # search-knowledge Edge Function (GOOGLE_API_KEY)

cd projects/agents/amaru
just sync
just serve
```

`search_context` calls the `search-knowledge` Edge Function (hybrid RAG). Local stack needs Supabase seeded with [`seed-assets/amaru-kb.sql`](../../supabase/seed-assets/amaru-kb.sql) and `just fn-serve` running. Without the function, the tool returns `TOOL_ERROR` with the real message (not `TOOL_NOT_FOUND`).

To refresh KB embeddings after editing [`seed-assets/amaru-kb.md`](../../supabase/seed-assets/amaru-kb.md): `cd projects/supabase && just generate-amaru-kb-seed`, then `just db-reset`.

`ADK_DEV_MODE=true` ensures a local Supabase `conversations` row with `id = ADK session.id` and mirrors `reply_with_*` for the playground.

**Manual RAG check:** turn 2+, ask “qué planes tienes para Bogotá” → `search_context` returns caminata ecológica / camping en la sabana with prices from the seed.

## Deploy

```bash
cd projects/agents/amaru
just deploy-stag-dry
just deploy-stag
just deploy            # prod after staging looks good
```

## Evals (HITL handoff)

Regression suite for derivation (bridge-only reply, turn gate, insufficient budget). Uses agents-cli + LLM judge in [`tests/eval/metrics.py`](./tests/eval/metrics.py).

```bash
cd projects/agents/amaru
just eval-handoff
just eval-handoff-grade
```

Dataset: [`tests/eval/datasets/handoff-es-dataset.json`](./tests/eval/datasets/handoff-es-dataset.json).

Offline sanity: `uv run python -m pytest tests/test_handoff_eval_dataset.py -q`

## Manual check

1. Turn 1: greeting only; no handoff on strong booking intent (except human request or disability).
2. Turn 2+: plan + listed departure + confirm reserve that outing → personalized bridge only; no BANT JSON visible.
3. Explicit human request on turn 1 → bridge only.
4. Insufficient budget → blocks plan+date and custom group; does **not** block human request or disability.
5. List pick / date + logistics → ask once if they reserve **that** outing; no handoff that turn.
6. No published date fits → offer custom group; handoff only if they accept.
