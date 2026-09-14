# Data Model: Conversational Agent Host Proof

**Feature**: `001-python-adk-poc` | **Date**: 2026-09-14

Storage: lightweight SQLite file for product stub (`./data/poc.sqlite`), separate from ADK `DatabaseSessionService` SQLite (`./data/sessions.sqlite`). Redis holds only the ephemeral text buffer lists and arq job state.

## Entities

### Conversation

| Field | Type | Rules |
|-------|------|--------|
| `id` | UUID (PK) | Also used as ADK `session_id` |
| `status` | enum | `BOT_AUTO` \| `WAITING_HUMAN` \| `HUMAN_ACTIVE` \| `CLOSED` |
| `wa_id` | string | Channel identity (simulated sender or WhatsApp id); not the session id |
| `updated_at` | datetime | Updated on inbound / status change |

**Uniqueness**: At most one **open** conversation (`status != CLOSED`) per `wa_id`. Find-or-create on inbound.

**Relationships**: Has many InboxMessage; 1:1 logical link to ADK session with `session_id = id`.

### InboxMessage

| Field | Type | Rules |
|-------|------|--------|
| `id` | UUID (PK) | |
| `conversation_id` | UUID (FK) | |
| `role` | enum | `customer` \| `bot` \| `operator` |
| `kind` | enum | `text` \| `buttons` \| `list` \| `location` \| `media` \| `choice` |
| `body` | string | Inbox fallback text (prompt, caption, option title, etc.) |
| `payload_json` | JSON | Renderable details per kind (see mapping) |
| `source` | string (optional) | e.g. `ask_choice`, `inbound`, `operator`, `whatsapp` |
| `created_at` | datetime | |

**Not** the agent's prompt history. Operator UI / debug reads this table only.

#### `payload_json` mapping

| Kind | `body` | `payload_json` |
|------|--------|----------------|
| `text` | message text | `{}` |
| `buttons` | prompt | `{ prompt, options: [{id,title}], functionCallId? }` — full options |
| `list` | prompt | `{ prompt, buttonLabel?, sections \| options }` |
| `location` | name or `"lat,lng"` | `{ latitude, longitude, name, address }` |
| `media` | caption or filename | `{ url, mimeType, caption }` |
| `choice` | option title if known else id | `{ buttonId }` |

### SentToolCall (idempotency)

| Field | Type | Rules |
|-------|------|--------|
| `id` | string (PK) | ADK `function_call_id` |
| `conversation_id` | UUID | |
| `tool_name` | string | e.g. `ask_choice` |
| `created_at` | datetime | |

Used so arq retry does not call `send_buttons` twice for the same call.

### WhatsAppDedup (optional helper)

| Field | Type | Rules |
|-------|------|--------|
| `message_id` | string (PK) | WhatsApp inbound message id |
| `seen_at` | datetime | |

May be replaced by PyWa `skip_duplicate_updates` plus a short Redis TTL set; either is acceptable if SC-019 de-dupe holds.

### Inbound text buffer (Redis, not SQL)

- Key: `buffer:{conversationId}`
- Value: list of text payloads (JSON strings or raw text)
- Lifecycle: RPUSH on inbound text; drained+deleted atomically by processor; follow-up job if non-empty after run

### Agent memory event (ADK-owned)

Not modeled in POC tables. Owned by `DatabaseSessionService` / session events.

Must include: user content, model content, small `ask_choice` args, short/null tool result, `function_response` with `buttonId`.

Must **not** include: channel interactive / Graph JSON.

### Outbound channel item (in-process + dual-write)

`ChannelService` (fake sink) remains the assertion target. Every send the operator must see is also inserted as InboxMessage. WhatsApp sink delivers to the network when credentials exist.

### Decision record

File artifact (`RESULTS.md`), not a DB entity.

## State transitions — Conversation.status

```text
(new) --> BOT_AUTO
BOT_AUTO --handoff--> WAITING_HUMAN
WAITING_HUMAN --release--> BOT_AUTO
BOT_AUTO|WAITING_HUMAN|HUMAN_ACTIVE --close--> CLOSED
CLOSED --new inbound same wa_id--> (new) BOT_AUTO  # new id

HUMAN_ACTIVE: no dedicated transition action in this POC.
If status is already HUMAN_ACTIVE, inbound skip rules match WAITING_HUMAN.
```

## Validation rules

1. Open conversation lookup is by `wa_id` where `status != CLOSED`.
2. Agent session id always equals `conversations.id` on the decision path.
3. Text buffer never contains button clicks or handoff actions.
4. Click with pending choice → resume + inbox `choice`; click without pending → inbox `choice` only, no agent.
5. Operator reply always dual-writes: channel + inbox + ADK `append_event`.
6. Takeover does not cancel already-scheduled arq jobs for that conversation.
7. WhatsApp inbound uses the same find-or-create rules; `wa_id` is the sender identifier.
8. Public HTTP bodies reject missing required fields (Pydantic).

## Volume assumptions

Demo scale: few conversations, short buffers, Redis local. No multi-tenant isolation in the stub.
