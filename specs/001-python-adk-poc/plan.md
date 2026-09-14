# Implementation Plan: Conversational Agent Host Proof

**Branch**: `001-python-adk-poc` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-python-adk-poc/spec.md`

## Summary

Prove go/no-go for putting an in-process Google ADK Python `Runner` behind a durable Redis job queue in a FastAPI host — behavioral parity with the NestJS TypeScript proof ([nestjs-adk](https://github.com/nicobytes/nestjs-adk)): immediate HTTP ack with `conversationId`, Redis text debounce + follow-up drain, retry/restart survival, Eve-style pause/resume on jobs, conversation UUID as ADK session id, HITL skip for post-handoff inbound, operator `append_event` dual-write, inbox vs session gist, and idempotent `ask_choice` side effects. Additionally, make live WhatsApp a first-class channel via [PyWa](https://pywa.readthedocs.io/en/latest/) (same conversation/queue path; skipped when credentials absent). Deliverable is `RESULTS.md`. Decision path is `/inbound` + queue + SQLite stub; WhatsApp is exercised when configured but does not replace simulated-channel evidence.

## Technical Context

**Language/Version**: Python 3.11+ (strict typing: Pydantic v2 models at all public boundaries; `pyright`/`mypy` strict optional)

**Primary Dependencies**: FastAPI + uvicorn; `google-adk[db]`; `arq` + Redis; SQLAlchemy/aiosqlite for POC stub; `pywa[server]` / `pywa_async` for WhatsApp; `httpx` for TestClient; `pytest` + `pytest-asyncio`

**Storage**: ADK `DatabaseSessionService` SQLite (`SESSION_DB_URL=sqlite+aiosqlite:///./data/sessions.sqlite`); POC stub SQLite (`POC_DB_URL=sqlite+aiosqlite:///./data/poc.sqlite`); Redis for arq jobs + `buffer:{conversationId}` lists

**Testing**: pytest + httpx `AsyncClient` / FastAPI lifespan; real arq worker preferred (in-process via lifespan for Nest parity); `pytest.mark.skipif(not GOOGLE_API_KEY)` for live Gemini cases

**Target Platform**: Local macOS/Linux FastAPI process; Redis on localhost:6379 (Docker acceptable)

**Project Type**: Single FastAPI web-service POC (monolith process; separate arq worker process only if isolation fails — document, do not build orchestration)

**Performance Goals**: Ack < 100ms while turn ~1.5s; cross-conversation HTTP/health < 200ms during yielding turn; debounce window ~400ms

**Constraints**: No await-job-finished in inbound; no timer-as-queue; no production CRM schema; decision path is simulated inbound; WhatsApp skipped without credentials; early stop if A1/A4 fail or Redis blocked ~1h; serialize per-conversation ADK runs (Python ADK session concurrency caveats); queue name must not collide with Nest (`fastapi-adk-messages`)

**Scale/Scope**: Demo fidelity, one org/agent; ~20 named automated cases + RESULTS.md; optional lightweight routing brain (P3); optional conversation debug view (P3)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status |
|------|--------|
| Project constitution principles | **N/A** — `.specify/memory/constitution.md` is still an unfilled template; no enforceable gates beyond this feature’s FR/SC |
| Spec quality (stakeholder WHAT/WHY) | Pass — plan may name FastAPI/arq/ADK/PyWa; implementation stays out of `spec.md` |
| No unjustified multi-project split | Pass — single FastAPI app (+ optional documented worker process only if A5 fails) |
| Early-stop / blocked Redis documented | Pass — research §1 / FR-040 |

**Post-design re-check**: Still N/A for constitution template. Design artifacts stay within single-app structure; contracts cover decision-path HTTP + WhatsApp webhook; no production CRM schema.

## Project Structure

### Documentation (this feature)

```text
specs/001-python-adk-poc/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── inbound-api.md
│   └── whatsapp-api.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
app/
├── __init__.py
├── main.py                 # FastAPI app factory + lifespan (Redis, arq worker, ADK host)
├── config.py               # pydantic-settings
├── constants.py
├── adk/                    # AdkHost, ask_choice LongRunningFunctionTool, observe, events
├── agents/                 # default agent + optional lightweight routing brain
├── channel/                # ChannelSink protocol, fake ChannelService, dual-write to inbox
├── conversations/          # ConversationStore (POC SQLite), status, inbox view
├── queue/                  # arq enqueue helpers, buffer, TurnService, worker functions
├── http/                   # routers: inbound, interactive, operator, conversations, health
└── adapters/
    └── whatsapp/           # PyWa wiring → same enqueue path as simulated inbound

tests/
├── conftest.py             # Redis + poc/session sqlite fixtures, app harness
├── test_queue_ack.py       # A1…
└── …                       # named cases A–I + WhatsApp skip/pass

data/
├── sessions.sqlite         # ADK
└── poc.sqlite              # conversations / messages / sent_tool_calls

RESULTS.md                  # go/no-go deliverable (repo root)
.pyproject.toml             # deps + tool config (uv)
.env.example
```

**Structure Decision**: Replace the hello-world `main.py` with an `app/` package (single deployable). Keep WhatsApp as an adapter that calls the same conversation/queue services. Do not create a second product service unless A5 fails (then only document `arq` CLI worker).

## Complexity Tracking

> No constitution violations to justify. Intentional complexity vs sync inbound:

| Choice | Why Needed | Simpler Alternative Rejected Because |
|--------|------------|-------------------------------------|
| arq + Redis | Spec requires durable delay/retry/restart and Nest/Bull-comparable buffer | `asyncio.sleep` / BackgroundTasks fail A3/A4 and FR-040 |
| Separate poc.sqlite | Avoid fighting ADK session schema | Stuffing CRM tables into session DB couples migrations |
| TurnService + worker only | FR-011: agent not invoked from accept path | Router→`run_async` sync fails A1 |
| sent_tool_calls table | FR-015 idempotency across job retry | In-memory set lost on restart mid-retry |
| Per-conversation lock | Python ADK session concurrency risks + click serialization | Parallel `run_async` on same session can corrupt history |
| PyWa adapter | Spec requires live WhatsApp when credentials present | Raw Graph client reinvented; user requested typed PyWa |

## Phase 0 & Phase 1 outputs

- [research.md](./research.md) — queue, buffer, identity, append_event, dual-write, idempotency, HITL, PyWa, typing
- [data-model.md](./data-model.md) — Conversation, InboxMessage, SentToolCall, Redis buffer, status transitions
- [contracts/inbound-api.md](./contracts/inbound-api.md) — decision-path HTTP
- [contracts/whatsapp-api.md](./contracts/whatsapp-api.md) — webhook + channel behavior
- [quickstart.md](./quickstart.md) — Redis, tests, RESULTS

Next command: `/speckit-tasks`
