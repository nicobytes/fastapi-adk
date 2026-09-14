# Tasks: Conversational Agent Host Proof

**Input**: Design documents from `/specs/001-python-adk-poc/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the feature specification and quickstart mandate fixed named automated cases for the go/no-go verdict.

**Organization**: Tasks are grouped by user story (US1–US13) so each story can be implemented and validated independently. **Early stop**: if US1 (A1) or US2 (A4) fails after implementation, write RESULTS.md and stop — later stories do not justify the queue.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US13)
- Paths are repository-relative under `app/` and `tests/`

## Path Conventions

Single FastAPI project: `app/`, `tests/` at repository root (pytest under `tests/`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package layout, dependencies, and env scaffolding

- [x] T001 Create `app/` package tree (`adk/`, `agents/`, `channel/`, `conversations/`, `queue/`, `http/`, `adapters/whatsapp/`) and `tests/` per `specs/001-python-adk-poc/plan.md`
- [x] T002 Add dependencies to `pyproject.toml`: `google-adk[db]`, `arq`, `redis`, `aiosqlite`, `sqlalchemy`, `pydantic-settings`, `pywa[server]`, `pytest`, `pytest-asyncio`, `httpx`, `pyright` (or mypy)
- [x] T003 [P] Create `.env.example` with `GOOGLE_API_KEY`, `REDIS_URL`, `SESSION_DB_URL`, `POC_DB_URL`, WhatsApp vars
- [x] T004 [P] Create `app/config.py` with pydantic-settings defaults (`REDIS_URL`, `SESSION_DB_URL=sqlite+aiosqlite:///./data/sessions.sqlite`, `POC_DB_URL=sqlite+aiosqlite:///./data/poc.sqlite`, queue name `fastapi-adk-messages`)
- [x] T005 [P] Create `app/constants.py` with `DEFAULT_AGENT_ID`, `USER_ID`, `BUFFER_MS=0.4`, `APP_NAME`
- [x] T006 [P] Document Redis prerequisite and decision-path vs WhatsApp in `README.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared stores, ADK host skeleton, arq wiring, harness, and contract DTOs that every story needs

**⚠️ CRITICAL**: No user story work until this phase completes

- [x] T007 Implement POC SQLite schema + `ConversationStore` (find-or-create open by `wa_id`) in `app/conversations/store.py`
- [x] T008 [P] Implement InboxMessage insert/list helpers in `app/conversations/messages.py`
- [x] T009 [P] Implement `sent_tool_calls` idempotency store in `app/conversations/sent_tool_calls.py`
- [x] T010 [P] Define Pydantic enums/models for Conversation status and inbox kinds in `app/conversations/types.py`
- [x] T011 Create `ChannelSink` protocol + fake `ChannelService` (in-memory send log) in `app/channel/types.py` and `app/channel/service.py`
- [x] T012 Create `AdkHost` skeleton (`Runner` + `DatabaseSessionService`, session lock) in `app/adk/host.py`
- [x] T013 [P] Create default LlmAgent factory stub in `app/agents/default.py`
- [x] T014 Implement Redis text buffer helpers (`RPUSH`, atomic drain, `LLEN`) in `app/queue/buffer.py`
- [x] T015 Create `TurnService` skeleton (text turn / button resume; no router→`run_async`) in `app/queue/turn.py`
- [x] T016 Create arq worker functions + `WorkerSettings` (queue `fastapi-adk-messages`) calling `TurnService` in `app/queue/worker.py`
- [x] T017 Create enqueue helpers (`enqueue_text`, `enqueue_button`) with `_job_id` / `_defer_by` in `app/queue/enqueue.py`
- [x] T018 Wire FastAPI app factory + lifespan (settings, stores, Redis pool, optional in-process arq worker) in `app/main.py`
- [x] T019 [P] Add Pydantic request/response models per `specs/001-python-adk-poc/contracts/inbound-api.md` in `app/http/schemas.py`
- [x] T020 [P] Add `GET /health` → `{ "ok": true }` in `app/http/health.py` and include router in `app/main.py`
- [x] T021 Create pytest harness fixtures (temp data dirs, Redis, ASGI client, lifespan) in `tests/conftest.py`
- [x] T022 [P] Add `tests/has_key.py` helper (`GOOGLE_API_KEY` present) for live Gemini skips

**Checkpoint**: Foundation ready — user stories can proceed (prefer P1 order; stop after A1/A4 failure)

---

## Phase 3: User Story 1 - Channel acknowledged before agent finishes (Priority: P1) 🎯 MVP

**Goal**: HTTP ack < 100ms with `conversationId`; turn runs in arq with retry; delayed job survives process restart

**Independent Test**: Slow turn (~1.5s) still acks fast; forced fail then success within 3 attempts; dispose app with delayed job then recreate against same Redis + SQLite and job runs

### Tests for User Story 1

> Write tests first; ensure they fail before implementation

- [x] T023 [P] [US1] Add `test_returns_http_before_the_runner_finishes` in `tests/test_queue_ack.py`
- [x] T024 [P] [US1] Add `test_retries_a_failed_job_and_then_runs_the_agent` in `tests/test_queue_retry.py`
- [x] T025 [P] [US1] Add `test_runs_a_delayed_job_after_process_restart` in `tests/test_queue_restart.py`

### Implementation for User Story 1

- [x] T026 [US1] Implement `POST /inbound` find-or-create, persist customer text, enqueue only (no await `run_async`) in `app/http/inbound.py`
- [x] T027 [US1] Implement `TurnService` text path invoking `AdkHost` with `session_id = conversation.id` in `app/queue/turn.py`
- [x] T028 [US1] Configure worker retries (`max_tries=3`, `Retry(defer=1)`) and ensure HTTP never awaits job result in `app/queue/worker.py` / `app/queue/enqueue.py`
- [x] T029 [US1] Return `{ conversationId, status, accepted: true }` within ack SLA from `app/http/inbound.py`

**Checkpoint**: US1 pass → continue. US1 A1 fail → fill RESULTS and stop.

---

## Phase 4: User Story 2 - Rapid texts become one turn (Priority: P1)

**Goal**: Debounce window ~400ms batches texts; follow-up drains mid-run arrivals; clicks not in text list

**Independent Test**: Three rapid POSTs → one `run_async`; extra text during busy job appears in follow-up; button path separate

### Tests for User Story 2

- [x] T030 [P] [US2] Add `test_batches_three_inbound_texts_into_one_run_async` in `tests/test_queue_buffer.py`
- [x] T031 [P] [US2] Add `test_follow_up_job_drains_texts_that_arrived_while_busy` in `tests/test_queue_buffer.py`

### Implementation for User Story 2

- [x] T032 [US2] On text inbound: `RPUSH` + enqueue with `_job_id=conversationId`, `_defer_by=BUFFER_MS` in `app/http/inbound.py` and `app/queue/enqueue.py`
- [x] T033 [US2] Drain list atomically, join texts with `\n`, single turn; if `LLEN > 0` after, enqueue follow-up `_job_id=f"{conversationId}-{ts}"` defer 0 in `app/queue/worker.py`
- [x] T034 [US2] Implement `POST /inbound/interactive` → button jobs (`_defer_by=0`, not text buffer) in `app/http/inbound.py` and `app/queue/enqueue.py`

**Checkpoint**: US2 A4 fail → RESULTS and stop (queue not worth it).

---

## Phase 5: User Story 3 - Busy conversation does not freeze others (Priority: P1)

**Goal**: Measure whether yielding `run_async` keeps other conversations responsive; document separate worker if not

**Independent Test**: During ~1.5s async wait turn, other conversation inbound or `GET /health` succeeds < 200ms

### Tests for User Story 3

- [x] T035 [P] [US3] Add `test_serves_another_conversation_while_run_async_in_flight` in `tests/test_queue_isolation.py`

### Implementation for User Story 3

- [x] T036 [US3] Provide async-yielding delay path for A5 (tool or test double; no sync busy-loop) in `app/adk/yielding_delay.py` or `tests/helpers/yielding_delay.py`
- [x] T037 [US3] Create `RESULTS.md` stub at repo root with isolation / “worker aparte” row template

**Checkpoint**: Isolation evidence recorded; do not build a separate product worker service in this POC

---

## Phase 6: User Story 4 - Choice pause, resume, no spam (Priority: P1)

**Goal**: `ask_choice` on queue jobs; resume via `function_response`; restart-safe pending choice; click waits if turn active; stray click inbox-only; idempotent send_buttons; no leftover prose

**Independent Test**: Pause then click; restart between; retry after send; overlapping click serializes; stray click stored without agent

### Tests for User Story 4

- [x] T038 [P] [US4] Add `test_pauses_on_ask_choice_in_a_queue_job_and_resumes_with_function_response` in `tests/test_queue_eve.py` (`skipif` without key)
- [x] T039 [P] [US4] Add `test_resumes_a_paused_choice_after_process_restart` in `tests/test_queue_eve_restart.py`
- [x] T040 [P] [US4] Add `test_ask_choice_send_buttons_is_idempotent_across_job_retry` in `tests/test_queue_ask_choice_idempotent.py`
- [x] T041 [P] [US4] Add `test_does_not_send_extra_text_when_ask_choice_pauses` in `tests/test_queue_observe_pause.py`
- [x] T042 [P] [US4] Add overlapping-click wait test covering SC-017 in `tests/test_queue_click_serialize.py`
- [x] T043 [P] [US4] Add stray-click test (no pending → inbox only) covering SC-018 in `tests/test_queue_stray_click.py`

### Implementation for User Story 4

- [x] T044 [US4] Implement `ask_choice` as `LongRunningFunctionTool` sending buttons during execute in `app/adk/ask_choice.py`
- [x] T045 [US4] Implement button job → `TurnService.resume` / `AdkHost.resume` with pending from session events only in `app/queue/turn.py` and `app/adk/host.py`
- [x] T046 [US4] Enforce per-conversation serialization so click jobs wait for active text turn in `app/queue/conversation_lock.py` and `app/queue/worker.py`
- [x] T047 [US4] Stray click: insert inbox `kind=choice`, skip agent in `app/queue/turn.py`
- [x] T048 [US4] Gate `send_buttons` on `sent_tool_calls` by `function_call_id` in `app/adk/ask_choice.py` and `app/conversations/sent_tool_calls.py`
- [x] T049 [US4] Suppress leftover model prose on pause in `app/adk/host.py` (observe/stream handler)

**Checkpoint**: Choice/resume/idempotency/prose rules green on decision path

---

## Phase 7: User Story 5 - Conversation is not channel identity (Priority: P2)

**Goal**: `conversations.id` is ADK session id; `wa_id` separate; close creates new session

**Independent Test**: Two `waId`s → two conversations; same `waId` reuses open; close then inbound → new UUID/session

### Tests for User Story 5

- [x] T050 [P] [US5] Add `test_uses_conversation_uuid_as_adk_session_id` in `tests/test_conversation_identity.py`

### Implementation for User Story 5

- [x] T051 [US5] Bind channel with `conversation_id` + store `wa_id` for sink addressing in `app/queue/turn.py` / `app/channel/service.py`
- [x] T052 [US5] Implement `POST /conversations/{id}/close` → `CLOSED` in `app/http/conversations.py`
- [x] T053 [US5] Ensure find-or-create skips `CLOSED` and allocates new UUID + ADK session in `app/conversations/store.py`

**Checkpoint**: Identity split proven; no channel-derived string as session on decision path

---

## Phase 8: User Story 6 - Human takeover silences agent (Priority: P2)

**Goal**: Post-handoff inbound stores message and skips agent; already-scheduled jobs still run; release restores bot; no HUMAN_ACTIVE action

**Independent Test**: Handoff then inbound → no runner; set HUMAN_ACTIVE in store → same skip; scheduled job after handoff still runs; release then inbound runs agent

### Tests for User Story 6

- [x] T054 [P] [US6] Add `test_skips_the_runner_when_conversation_is_waiting_human` in `tests/test_hitl_skip.py`
- [x] T055 [P] [US6] Add already-scheduled-job-still-runs-after-handoff case in `tests/test_hitl_scheduled_job.py`

### Implementation for User Story 6

- [x] T056 [US6] Implement `POST /conversations/{id}/handoff` → `WAITING_HUMAN` and `POST .../release` → `BOT_AUTO` in `app/http/conversations.py`
- [x] T057 [US6] At accept time only: if `WAITING_HUMAN`/`HUMAN_ACTIVE`, persist customer message and do not enqueue agent turn in `app/http/inbound.py`
- [x] T058 [US6] Ensure worker does not cancel already-scheduled jobs on status change (FR-020a) in `app/queue/worker.py` / `app/queue/turn.py`

**Checkpoint**: HITL skip for new inbound; scheduled-job clarification honored

---

## Phase 9: User Story 7 - Operator reply visible to next agent turn (Priority: P2)

**Goal**: Operator text to channel + inbox + `append_event` without `run_async`; next customer turn reflects fact

**Independent Test**: Operator “el precio es 100”; customer asks; reply mentions 100 (`skipif` without key)

### Tests for User Story 7

- [x] T059 [P] [US7] Add `test_operator_reply_is_visible_to_the_next_agent_turn` in `tests/test_operator_append_event.py` (`skipif` without key)

### Implementation for User Story 7

- [x] T060 [US7] Implement `POST /operator/reply` with `conversationId`, `send_text`, inbox insert, `append_event`, no `run_async` in `app/http/operator.py`
- [x] T061 [US7] Add helper to build operator/user event and reload session before append in `app/adk/events.py`

**Checkpoint**: Dual-write to session without prompt injection

---

## Phase 10: User Story 8 - Inbox and agent memory stay separate (Priority: P2)

**Goal**: After text turn, both stores populated; agent reads only session; inbox only from messages; survive restart

**Independent Test**: Customer+bot inbox rows and session events; restart; prove no messages→prompt assembly

### Tests for User Story 8

- [x] T062 [P] [US8] Add `test_inbox_and_adk_session_are_dual_write_not_prompt_injection` in `tests/test_dual_write_history.py`

### Implementation for User Story 8

- [x] T063 [US8] Persist customer + bot text inbox rows on successful BOT_AUTO text turn in `app/queue/turn.py` and/or channel dual-write hook in `app/channel/service.py`
- [x] T064 [US8] Ensure `AdkHost` assembles history only from session service (no inbox read) in `app/adk/host.py`

**Checkpoint**: F rules demonstrable without production CRM

---

## Phase 11: User Story 9 - Operator sees channel; agent remembers gist (Priority: P2)

**Goal**: Inbox `payload_json` for buttons/list/location/media/choice; session keeps small intent + gist/null; inbox renderable without parsing session

**Independent Test**: Named I tests for gist, args, choice row, location, inbox-only render

### Tests for User Story 9

- [x] T065 [P] [US9] Add `test_session_tool_result_is_a_summary_not_channel_json` in `tests/test_channel_crm_mapping.py`
- [x] T066 [P] [US9] Add `test_function_call_args_stay_small_intent_not_graph` in `tests/test_channel_crm_mapping.py`
- [x] T067 [P] [US9] Add `test_stores_buttons_payload_on_messages_when_ask_choice_sends` in `tests/test_channel_crm_mapping.py`
- [x] T068 [P] [US9] Add `test_resume_writes_option_id_to_session_and_choice_row_to_messages` in `tests/test_channel_crm_mapping.py`
- [x] T069 [P] [US9] Add `test_location_payload_is_in_messages_session_result_is_gist` in `tests/test_channel_crm_mapping.py`
- [x] T070 [P] [US9] Add `test_operator_inbox_does_not_require_parsing_session_events` in `tests/test_channel_crm_mapping.py`

### Implementation for User Story 9

- [x] T071 [US9] Dual-write all channel sends (`send_text`/`send_buttons`/`send_location`/`send_media`) to inbox with FR-028 mapping in `app/channel/service.py`
- [x] T072 [US9] Keep `ask_choice` return gist/null + `skip_summarization`; never persist interactive Graph in session in `app/adk/ask_choice.py`
- [x] T073 [US9] Add `to_inbox(messages)` helper used by tests/debug in `app/conversations/inbox_view.py`

**Checkpoint**: Inbox/gist split proven (I)

---

## Phase 12: User Story 10 - Live WhatsApp customer (Priority: P2)

**Goal**: PyWa webhook ack immediate; same conversation/queue path; text + buttons; de-dupe; signature verify; skip without credentials

**Independent Test**: With credentials, WhatsApp text + choice; without credentials, tests skip and RESULTS records `skip`

### Tests for User Story 10

- [x] T074 [P] [US10] Add WhatsApp unit tests for verify token + signature reject in `tests/test_whatsapp_webhook_security.py`
- [x] T075 [P] [US10] Add WhatsApp de-dupe test (same message_id ignored) in `tests/test_whatsapp_dedupe.py`
- [x] T076 [P] [US10] Add live or mocked “text + choice uses same enqueue path” test in `tests/test_whatsapp_channel.py` (`skipif` without WhatsApp env for live)

### Implementation for User Story 10

- [x] T077 [US10] Mount PyWa (`pywa_async`) on FastAPI with `webhook_endpoint=/whatsapp/webhook` in `app/adapters/whatsapp/client.py` and `app/main.py`
- [x] T078 [US10] Map inbound text/button handlers → find-or-create + enqueue (same as simulated) in `app/adapters/whatsapp/handlers.py`
- [x] T079 [US10] Implement `WhatsAppChannelSink` delivering text/buttons/list/location/media via PyWa in `app/adapters/whatsapp/sink.py`
- [x] T080 [US10] Wire de-dupe, read/typing indicator, and skip-when-unconfigured behavior in `app/adapters/whatsapp/handlers.py` / `app/adapters/whatsapp/dedupe.py`
- [x] T081 [US10] Optional `POST /whatsapp/nudge` with care-window `409` in `app/adapters/whatsapp/routes.py`

**Checkpoint**: WhatsApp pass or skip recorded; simulated path remains decision evidence

---

## Phase 13: User Story 11 - Written go/no-go record (Priority: P1)

**Goal**: RESULTS.md answers all architecture questions with evidence, Nest parity, WhatsApp pass/skip/fail, overall recommendation

**Independent Test**: Reviewer can decide from RESULTS.md alone per FR-033–037

### Implementation for User Story 11

- [x] T082 [US11] Expand `RESULTS.md` with the User Story 11 question table (empty results + Nest parity + WhatsApp rows)
- [x] T083 [US11] Fill RESULTS.md from test outcomes (A–I, clarifications, processor worth-it, go/no-go, specialist port no/later, Nest parity, WhatsApp)
- [x] T084 [US11] Link RESULTS.md and decision-path / WhatsApp notes from `README.md`

**Checkpoint**: Verdict written; early-stop rows allowed if A1/A4 failed earlier

---

## Phase 14: User Story 12 - Lightweight routing brain lab (Priority: P3)

**Goal**: Opt-in lightweight routing brain; lab routing with fake classification; not required for queue go

**Independent Test**: Select brain via `agentId`; greeting stays bot; human-request path sets waiting-for-human with fake classifier

### Tests for User Story 12

- [x] T085 [P] [US12] Add lightweight brain gate/routing tests in `tests/test_amaru_lite_gate.py`

### Implementation for User Story 12

- [x] T086 [US12] Implement opt-in lightweight routing agent module in `app/agents/amaru_lite/`
- [x] T087 [US12] Wire `agentId` selection in `app/agents/registry.py` and inbound path without changing default decision agent

**Checkpoint**: Lab brain optional; specialist port remains no/later

---

## Phase 15: User Story 13 - Conversation inspection view (Priority: P3)

**Goal**: Debug endpoint shows status, inbox, short session preview; not required for go

**Independent Test**: After one inbound turn, `GET /conversations/{id}/debug` shows inbox + sessionEventCount

### Tests for User Story 13

- [x] T088 [P] [US13] Add debug endpoint contract test in `tests/test_conversation_debug.py`

### Implementation for User Story 13

- [x] T089 [US13] Implement `GET /conversations/{id}/debug` (inbox via `to_inbox`, session preview, no CRM-only fields) in `app/http/conversations.py`

**Checkpoint**: Inspection view available for reviewers

---

## Phase 16: Polish & Cross-Cutting Concerns

**Purpose**: Docs, typing, and validation pass across stories

- [x] T090 [P] Align README Redis / `uv run pytest` / live Gemini / PyWa notes with `specs/001-python-adk-poc/quickstart.md`
- [x] T091 [P] Add `pyrightconfig.json` or pyproject `[tool.pyright]` / `[tool.mypy]` and fix public-boundary typing in `app/http/` and `app/conversations/`
- [x] T092 Run full `uv run pytest` (with and without `GOOGLE_API_KEY` / WhatsApp env as applicable) and fix regressions in `tests/` and `app/`
- [x] T093 Verify no decision-path code awaits job finished or uses `wa_id` as ADK session id (grep + fix in `app/http/` and `app/queue/`)
- [x] T094 Remove obsolete root hello-world `main.py` or re-export `app.main:app` for `fastapi dev`
- [x] T095 Mark Spec Kit checklist notes updated if needed in `specs/001-python-adk-poc/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: After Setup — **blocks all stories**
- **US1 → US2 → US3**: Prefer sequential; **stop if A1 or A4 fail**
- **US4**: After US1–US2 (needs queue jobs); benefits from US5 identity but can use conversation UUID from foundation
- **US5–US9**: After foundation; best after US1 inbound shape exists; can parallelize across developers after US2
- **US10**: After US1–US2 enqueue path (and ideally US4 for buttons); can parallelize with US5–US9 on adapter files
- **US11**: After experiments complete (or early stop)
- **US12–US13**: Optional P3 after decision-path green
- **Polish**: After desired stories + RESULTS

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|--------|
| US1 | Phase 2 | MVP / A1–A3 |
| US2 | US1 enqueue path | A4; early-stop gate |
| US3 | US1 | A5 measurement |
| US4 | US1–US2 | Eve on jobs + clarifications |
| US5 | Phase 2 + US1 inbound | Close + identity |
| US6 | US5 statuses | HITL; FR-020a |
| US7 | US5 conversationId | append_event |
| US8 | US1 turn + inbox writes | Dual-write F |
| US9 | US4 ask_choice + channel | Mapping I |
| US10 | US1–US2 (+ US4 for buttons) | PyWa; skip OK |
| US11 | Evidence from above | RESULTS |
| US12 | Phase 2 + US1 | Optional P3 |
| US13 | US5 + US8 inbox | Optional P3 |

### Within Each User Story

- Tests first (fail), then implementation
- Stores/services before routers where applicable
- Checkpoint before next priority when following early-stop rules

### Parallel Opportunities

- Phase 1: T003–T006 in parallel after T001–T002
- Phase 2: T008–T010 parallel; T013 parallel with T012; T019–T020 / T022 parallel
- Per story: all `[P]` test tasks in that story can be written in parallel
- After US2: US5/US6/US7 and US10 adapter work can proceed on different files in parallel (watch `app/http/inbound.py` conflicts)
- US12 and US13 can run in parallel after US5/US8

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Add test_returns_http_before_the_runner_finishes in tests/test_queue_ack.py"
Task: "Add test_retries_a_failed_job_and_then_runs_the_agent in tests/test_queue_retry.py"
Task: "Add test_runs_a_delayed_job_after_process_restart in tests/test_queue_restart.py"

# Then implementation sequentially on shared queue/http files:
Task: "Implement POST /inbound enqueue-only in app/http/inbound.py"
Task: "Implement TurnService text path in app/queue/turn.py"
Task: "Wire worker retries in app/queue/worker.py"
```

---

## Parallel Example: User Story 9

```bash
Task: "Add session tool result gist test in tests/test_channel_crm_mapping.py"
Task: "Add function_call args test in tests/test_channel_crm_mapping.py"
Task: "Add buttons payload CRM test in tests/test_channel_crm_mapping.py"
# (same file — write as one PR/batch if single agent; [P] OK when splitting by test modules)
```

---

## Parallel Example: User Story 10

```bash
Task: "WhatsApp webhook security tests in tests/test_whatsapp_webhook_security.py"
Task: "WhatsApp dedupe tests in tests/test_whatsapp_dedupe.py"
# Then implementation:
Task: "Mount PyWa client in app/adapters/whatsapp/client.py"
Task: "Handlers → enqueue in app/adapters/whatsapp/handlers.py"
Task: "WhatsAppChannelSink in app/adapters/whatsapp/sink.py"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 Setup  
2. Phase 2 Foundational  
3. Phase 3 US1 (A1–A3)  
4. **STOP and VALIDATE** — if A1 fails, RESULTS + halt  

### Incremental Delivery (recommended)

1. US1 → US2 (A4) → **gate**  
2. US3 (A5 note)  
3. US4 (Eve/idempotency/prose/clicks)  
4. US5 → US6 → US7 → US8 → US9  
5. US10 WhatsApp (or skip)  
6. US11 RESULTS  
7. Optional US12–US13 + Polish  

### Early-stop rule

If A1 or A4 cannot pass without awaiting the job in HTTP or without real debounce/follow-up, complete US11 RESULTS as **no-go / not worth processor** and skip remaining implementation stories.

---

## Notes

- Decision evidence is simulated `/inbound` + arq + SQLite stub — not live WhatsApp alone  
- Do not clone production CRM schema  
- Clarifications: click serializes; scheduled job survives handoff; ack returns `conversationId`; stray click inbox-only; no HUMAN_ACTIVE action  
- Queue name `fastapi-adk-messages` — do not share Nest queues on the same Redis  
- `[P]` = different files / no incomplete-task dependency; avoid parallel edits to the same router without coordination  
- Total tasks: **T001–T095** (95)
