# Quickstart: Validate Conversational Agent Host Proof

**Feature**: `001-python-adk-poc`  
**Contracts**: [contracts/inbound-api.md](./contracts/inbound-api.md), [contracts/whatsapp-api.md](./contracts/whatsapp-api.md)  
**Data model**: [data-model.md](./data-model.md)

This guide is how a reviewer re-runs the go/no-go evidence after implementation. It is not the implementation itself.

## Prerequisites

- Python **3.11+** and **uv** (or pip)
- **Redis** on `localhost:6379` (or `REDIS_URL`)
- Optional: `GOOGLE_API_KEY` for live Gemini cases (choice pause, operator fact recall)
- Optional WhatsApp: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`

```bash
# Example Redis
docker run --rm -p 6379:6379 redis:7
```

If Redis cannot be started within ~1 hour of effort: stop, mark queue items blocked in `RESULTS.md`. Do not fake the queue with timers.

## Setup

```bash
uv sync
# Ensure SESSION_DB_URL / POC_DB_URL paths are writable under ./data/
uv run pytest
```

Decision path is `/inbound` + arq + SQLite stub. WhatsApp is additional when configured.

## Manual smoke (after implementation)

```bash
uv run fastapi dev
# or: uv run uvicorn app.main:app --reload
```

```bash
# Ack should return conversationId quickly
curl -s localhost:8000/inbound -H 'content-type: application/json' \
  -d '{"waId":"5215512345678","text":"hola"}'

# Interactive click uses conversationId from ack
curl -s localhost:8000/inbound/interactive -H 'content-type: application/json' \
  -d '{"conversationId":"<uuid>","buttonId":"b"}'

curl -s localhost:8000/conversations/<uuid>/handoff -X POST
curl -s localhost:8000/operator/reply -H 'content-type: application/json' \
  -d '{"conversationId":"<uuid>","text":"el precio es 100"}'
curl -s localhost:8000/conversations/<uuid>/release -X POST
curl -s localhost:8000/conversations/<uuid>/close -X POST
curl -s localhost:8000/health
```

If the worker is not embedded in lifespan, start it in a second terminal:

```bash
uv run arq app.queue.worker.WorkerSettings
```

## Automated evidence (fixed intents)

Implement tests that cover these intents (exact file names left to implementer):

1. Returns HTTP before the runner finishes — A1  
2. Retries a failed job and then runs the agent — A2  
3. Runs a delayed job after process restart — A3  
4. Batches three inbound texts into one `run_async` — A4  
5. Follow-up job drains texts that arrived while the worker was busy — A4  
6. Serves another conversation / health while a turn is in flight — A5  
7. Pauses on `ask_choice` in a queue job and resumes with `function_response` — B  
8. Resumes a paused choice after process restart — B  
9. Uses conversation UUID as ADK session id — C  
10. Skips the runner when conversation is `WAITING_HUMAN` — D  
11. Operator reply is visible to the next agent turn — E  
12. Inbox messages and ADK session are dual-write, not prompt injection — F  
13. `ask_choice` send_buttons is idempotent across job retry — G  
14. Does not send extra text when `ask_choice` pauses — H  
15–20. Session gist / inbox payload / choice / location / inbox-without-session (I)  
21. WhatsApp live text + choice **or** skipped without credentials  

Also cover clarifications:

- Click scheduled while turn active waits for that turn  
- Already-scheduled turn still runs after handoff; new inbound after handoff does not  
- Stray click → inbox only  
- Ack includes `conversationId`  
- Invalid public payloads → `422`

```bash
uv run pytest
GOOGLE_API_KEY=... uv run pytest
```

## Decision record

After experiments (or early stop on A1/A4 fail), fill **RESULTS.md** with every User Story 11 question, evidence pointers (test names), Nest parity row, WhatsApp pass/skip/fail, and overall go / no-go / yes-with-conditions.

## Expected outcomes for a theoretical go

- A1–A4, B, C, D, G, I pass  
- A5 pass **or** RESULTS notes separate worker required (not built here)  
- E and F pass **or** documented `append_event` workaround that is not inbox→prompt  
- Specialist-agent port remains **no / later**  
- WhatsApp `pass` or `skip` (not silent fail)
