# Research: Conversational Agent Host Proof

**Branch**: `001-python-adk-poc` | **Date**: 2026-09-14

## 1. Durable queue library

**Decision**: [arq](https://arq-docs.helpmanual.io/) with Redis (`REDIS_URL`, default `redis://127.0.0.1:6379`). Queue name: `fastapi-adk-messages` (do not share Nest’s `nestjs-adk-messages` / `messages` on the same Redis).

**Worker placement**: Prefer an **in-process** arq worker started from FastAPI lifespan (asyncio task) so the POC mirrors Nest’s in-process BullMQ worker and A5 can measure same-process isolation. If embedding is unreliable under pytest, run `arq app.queue.worker.WorkerSettings` as a companion process in quickstart and treat A5 failure as “separate background service required” (document only; do not build multi-service orchestration).

**Rationale**: arq is asyncio-native, supports `_job_id` dedup, `_defer_by` delayed jobs, `Retry(defer=…)`, and pessimistic re-queue on worker crash — closest BullMQ analogue in Python without Celery overhead. Spec forbids timer-as-queue (FR-040).

**Alternatives considered**:

| Option | Why rejected |
|--------|----------------|
| Celery + Redis | Heavier; sync-first; overkill for POC |
| RQ | Sync worker model fights FastAPI/ADK async |
| FastAPI `BackgroundTasks` / `asyncio.create_task` | Not durable; fails restart (A3) |
| Dramatiq | Fine, but arq maps better to async + job_id |
| Separate worker from day one | Only justified if A5 fails; document, do not build |

**Blocked path**: If Redis cannot be stood up within ~1 hour, mark queue items blocked in RESULTS and stop (no timer substitute).

---

## 2. Debounce / buffer pattern

**Decision**: Nest/Chatty-shaped buffer:

1. On text inbound: `RPUSH buffer:{conversationId}` + `enqueue_job('process_turn', conversation_id=…, kind='text', _job_id=conversationId, _defer_by=BUFFER_MS)`.
2. Duplicate `_job_id` while job key exists → arq returns `None`; text still lands in the list. Accept that.
3. Processor: atomic drain (`MULTI` `LRANGE` + `DEL`, or Lua), join texts with `\n`, one `run_async`.
4. After job finishes, if `LLEN > 0`, enqueue follow-up `_job_id=f"{conversationId}-{timestamp_ms}"` with `_defer_by=0`.
5. `BUFFER_MS = 0.4` seconds (tests).
6. Retries: `max_tries=3`, raise `Retry(defer=1)` (~1s) on transient failure.

**Button clicks**: Separate job `kind='button'`, `_defer_by=0`, unique `_job_id` per click (`{conversationId}:btn:{buttonId}:{ts}`). If a turn is already active for that conversation, the click waits (per-conversation asyncio lock / Redis lock). Do not mix clicks into the text list.

**Rationale**: Spec A4 + click serialization. Without follow-up drain, texts that arrive mid-run are lost.

**Alternatives considered**: One job per message (FR-036); debounce only in HTTP (no restart survival); Redis Streams consumer group (overkill).

---

## 3. Turn entrypoint vs HTTP accept

**Decision**: `TurnService` called **only** from the queue worker. Decision-path routers (`POST /inbound`, interactive, handoff, release, close) must not call `Runner.run_async` directly. `AdkHost` remains the ADK adapter; TurnService orchestrates status, buffer drain, and host calls.

**HITL**: Status for *new* inbound after takeover is checked at **accept** time (FR-020). An already-scheduled job still runs the agent (FR-020a) — worker must **not** re-check status to cancel that job.

**Rationale**: FR-011; Nest proved the same split.

**Alternatives considered**: Fire-and-forget `asyncio.create_task` from router (fails A2/A3/A4); await job result in HTTP (kills A1).

---

## 4. Conversation identity vs session

**Decision**: POC SQLite tables `conversations` + `messages` + `sent_tool_calls` in `./data/poc.sqlite` (separate from ADK `./data/sessions.sqlite`). `conversation.id` (UUID) **is** ADK `session_id`. `wa_id` stored on the row; never use channel-derived strings as session id on the decision path.

**Inbound**: `{ waId, text, agentId? }` → find-or-create open conversation (`status != CLOSED`) → `{ conversationId, status, accepted: true }`.

**Close**: `POST /conversations/{id}/close` → `CLOSED`; next inbound for that `waId` creates a new UUID/session.

**Rationale**: Spec User Story 5 / FR-017–019; parity with Nest data model.

**Alternatives considered**: Channel-derived session ids (product no-go); clone production CRM schema (out of scope).

---

## 5. Google ADK Python host

**Decision**:

- `google-adk[db]` with `DatabaseSessionService(db_url="sqlite+aiosqlite:///./data/sessions.sqlite")`.
- `Runner.run_async(...)` for turns; `LongRunningFunctionTool` for `ask_choice` (pause/resume with `function_response` + same `function_call_id`).
- Operator path: `session_service.append_event` **without** `run_async`.
- Tool result: return short gist / `None` + `skip_summarization` so session does not store channel Graph/interactive JSON.
- Auth: `GOOGLE_API_KEY` (Gemini). Model: `gemini-2.5-flash` or current flash default accepted by the installed SDK.
- **Serialize** `run_async` per `session_id` (asyncio lock). Python ADK has documented stale-session / concurrent `append_event` hazards under parallel runs.

**Rationale**: Official Python ADK is the Nest `@google/adk` counterpart; LongRunningFunctionTool + DatabaseSessionService are the pause/resume + restart story.

**Alternatives considered**: InMemorySessionService only (fails restart); hand-rolled history tables (no-go); Vertex Agent Runtime (out of scope).

**Risk**: Pin ADK version in lockfile; document any resume API differences vs Nest in RESULTS.

---

## 6. Operator visibility into agent memory

**Decision**: Operator reply → channel `send_text` + inbox `role=operator` + `append_event` (user/operator-authored) without generating a model reply. Reload session via `get_session` before append (ADK guidance for stale markers).

**Rationale**: FR-022–023. Copying inbox into prompt history is FR-027 no-go.

**Risk**: If the model ignores appended event shape, RESULTS documents fail; do not fall back to prompt injection.

---

## 7. Channel dual-write and gist

**Decision**:

- `ChannelSink` protocol: fake in-memory list for assertions + WhatsApp sink when configured.
- Every operator-visible send dual-writes `InboxMessage` with FR-028 payload mapping.
- `ask_choice` sends buttons during tool execute; returns gist/null + skip summarization.
- Stray click (no pending choice): inbox `kind=choice` only; no agent.

**Rationale**: Spec User Stories 8–9; Nest ChannelService pattern.

---

## 8. Idempotent `ask_choice` on retry

**Decision**: Persist `sent_tool_calls(id=function_call_id)`. On retry, if id already sent, skip `send_buttons`.

**Rationale**: FR-015. arq retries are at-least-once.

**Alternatives considered**: Memory-only set (fails restart mid-retry); hope ADK skips re-execute (still add durable lock).

---

## 9. Pause without leftover prose

**Decision**: Host observe/stream handler: when turn ends paused (long-running tool pending), do not `send_text` leftover model prose for that turn.

**Rationale**: FR-016 / SC-009.

---

## 10. HITL status transitions

**Decision**: Takeover → `WAITING_HUMAN` only. No dedicated HTTP action for `HUMAN_ACTIVE`. Tests may set `HUMAN_ACTIVE` via store for skip-rule coverage. Release → `BOT_AUTO`. Already-scheduled jobs after takeover still run (FR-020a).

---

## 11. WhatsApp via PyWa

**Decision**: Use **PyWa** (`pywa` / `pywa_async`) plugged into the FastAPI app (`server=app`, `webhook_endpoint=/whatsapp/webhook`). Handlers map text / button taps → same find-or-create + enqueue path as simulated inbound (channel identity = WhatsApp sender id). Outbound uses PyWa send APIs from a `WhatsAppChannelSink`.

**Security / ops**:

- `verify_token` for GET challenge.
- `app_secret` → signature validation (`X-Hub-Signature-256`); reject invalid when configured.
- `skip_duplicate_updates=True` (or explicit message-id store) for de-dupe.
- Mark read + typing indicator when supported before/while turn runs.
- Without `WHATSAPP_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID`, skip live WhatsApp tests; simulated path remains decision evidence.
- Proactive nudge outside customer-care window → refuse (409).

**Rationale**: Spec User Story 10; user requested PyWa as the typed WhatsApp alternative to Nest’s Graph client.

**Alternatives considered**: Raw Meta Graph HTTP (more glue, weaker typing); keep WhatsApp out of POC (fails user request).

**Scope cut**: Templates, Flows, calls, multi-WABA / per-tenant credentials out of scope.

---

## 12. Strict typing (TypeScript rigor)

**Decision**:

- All public request/response bodies are Pydantic v2 models (no untyped `dict` as public contract).
- `pydantic-settings` for env.
- `Protocol` for `ChannelSink`; TypedDicts or models for inbox payloads.
- Enable `pyright` (basic→strict over time) and/or `mypy --strict` on `app/`.
- Prefer `from __future__ import annotations`; no `Any` at router boundaries.

**Rationale**: Spec FR-041 / SC-020 and user requirement for TypeScript-like rigor.

---

## 13. Testing harness

**Decision**: pytest-asyncio + httpx ASGI client; fixtures start Redis (localhost or testcontainers), writable `./data` temp dirs, app lifespan with arq worker. Prefer real queue worker in tests. `skipif(not GOOGLE_API_KEY)` for live choice/operator-fact cases. A5: async sleep in tool (not CPU busy-loop). Restart: dispose app, recreate against same Redis + SQLite files.

**Rationale**: Spec SC-016; Nest harness parity.

---

## 14. Decision deliverable

**Decision**: `RESULTS.md` at repo root. Fill User Story 11 questions (including parity vs Nest + WhatsApp pass/skip/fail). Early stop if A1 or A4 fail.

---

## 15. Constitution

**Decision**: Project constitution file is still a placeholder template. No enforceable Spec Kit gates apply beyond this feature’s own FR/SC.

**Rationale**: `.specify/memory/constitution.md` has unfilled principle placeholders.

---

## 16. Optional P3 items

**Decision**: Lightweight routing brain (opt-in `agentId`) and `GET /conversations/{id}/debug` are optional; not required for queue go. Implement after P1/P2 evidence is green if time allows.
