# Contract: Decision-path HTTP API

**Feature**: `001-python-adk-poc`  
**Base**: FastAPI (same process as ADK host + preferred in-process arq worker).  
**Auth**: None (POC).  
**Related**: [data-model.md](../data-model.md), [whatsapp-api.md](./whatsapp-api.md)

This contract covers the **architecture decision path**. WhatsApp webhooks use the same conversation/queue services but are documented separately. A legacy `{ sessionId, text }` sync path may exist for demos; it is **not** go/no-go evidence.

All request/response bodies are strictly typed (Pydantic). Unknown fields may be ignored; missing required fields → `422`.

---

## POST /inbound

Accept customer text. Find-or-create open conversation. Buffer + schedule turn. Do **not** wait for the agent.

### Request

```json
{
  "waId": "5215512345678",
  "text": "hola",
  "agentId": "amaru"
}
```

| Field | Required | Notes |
|-------|----------|--------|
| `waId` | yes | Channel identity |
| `text` | yes | Non-empty |
| `agentId` | no | Defaults to POC default agent |

### Response `200` (within 100ms when turn is slow)

```json
{
  "conversationId": "11111111-1111-1111-1111-111111111111",
  "status": "BOT_AUTO",
  "accepted": true
}
```

### Behavior by status at accept time

| Status | Persist customer message | Schedule agent turn |
|--------|--------------------------|---------------------|
| `BOT_AUTO` | yes | yes (text buffer + delayed job) |
| `WAITING_HUMAN` / `HUMAN_ACTIVE` | yes | **no** |
| `CLOSED` | N/A (create new conversation first) | yes on new open row |

### MUST NOT

- Await job finished / `run_async` before responding
- Use `waId` as ADK session id

---

## POST /inbound/interactive

Accept a button click. Schedule immediately (`_defer_by=0`), separate from text buffer. If a turn for that conversation is active, run only after it finishes.

### Request

```json
{
  "conversationId": "11111111-1111-1111-1111-111111111111",
  "buttonId": "b"
}
```

| Field | Required | Notes |
|-------|----------|--------|
| `conversationId` | yes | From prior `/inbound` ack |
| `buttonId` | yes | Option id |
| `agentId` | no | Optional agent override |

### Response `200`

```json
{
  "conversationId": "11111111-1111-1111-1111-111111111111",
  "accepted": true
}
```

### When job runs

| Pending choice? | Effect |
|-----------------|--------|
| yes | Resume with `function_response` / option id; inbox `kind=choice` |
| no | Inbox `kind=choice` only; **no** agent turn; **no** invented customer text |

---

## POST /conversations/{id}/handoff

### Response `200`

```json
{ "conversationId": "...", "status": "WAITING_HUMAN" }
```

Sets `WAITING_HUMAN` only. Does not cancel already-scheduled jobs.

---

## POST /conversations/{id}/release

### Response `200`

```json
{ "conversationId": "...", "status": "BOT_AUTO" }
```

---

## POST /conversations/{id}/close

### Response `200`

```json
{ "conversationId": "...", "status": "CLOSED" }
```

Next `/inbound` for the same `waId` creates a new conversation id / ADK session.

---

## POST /operator/reply

Send operator text to the channel, store inbox row, append to ADK session **without** `run_async`.

### Request

```json
{
  "conversationId": "11111111-1111-1111-1111-111111111111",
  "text": "el precio es 100"
}
```

### Response `200`

```json
{
  "conversationId": "11111111-1111-1111-1111-111111111111",
  "accepted": true
}
```

### MUST

- Channel sink `send_text` (fake and/or WhatsApp when targeted)
- Insert inbox `role=operator`, `kind=text`
- `session_service.append_event` (or equivalent) so the next agent turn can see the fact

### MUST NOT

- Call `run_async` / generate a model reply at this moment

---

## GET /health

### Response `200`

```json
{ "ok": true }
```

Used by isolation test (A5) while another conversation’s turn is in flight.

---

## GET /conversations/{id}/debug (optional)

Human inspection; not required for go.

```json
{
  "conversation": { "id": "...", "status": "BOT_AUTO", "waId": "..." },
  "messages": [ /* inbox rows */ ],
  "sessionEventCount": 12,
  "sessionPreview": [ /* short event summaries, not Graph payloads */ ]
}
```

Must not add production-only CRM columns.

---

## Error responses (minimal)

| Status | When |
|--------|------|
| `422` | Validation failure (Pydantic) |
| `404` | Unknown `conversationId` |
| `409` | Optional: conflicting close/handoff; WhatsApp care-window closed for proactive send |

---

## Compatibility note

Legacy `{ sessionId, text }` on `/inbound` is **not** the decision contract. Keep only if needed for temporary demos; go/no-go tests use `waId` + returned `conversationId`.
