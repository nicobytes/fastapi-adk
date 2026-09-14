# Contract: WhatsApp channel (PyWa)

**Feature**: `001-python-adk-poc`  
**Related**: [inbound-api.md](./inbound-api.md), [data-model.md](../data-model.md)  
**Library**: [PyWa](https://pywa.readthedocs.io/en/latest/) (`pywa` / `pywa_async`) mounted on the FastAPI app

Live WhatsApp is a **first-class channel** when credentials are present. It is **not** a substitute for simulated `/inbound` go/no-go evidence. When credentials are absent, skip live scenarios and record `skip` in RESULTS.

---

## Configuration (env)

| Variable | Required for live | Notes |
|----------|-------------------|--------|
| `WHATSAPP_TOKEN` | yes | Cloud API token |
| `WHATSAPP_PHONE_NUMBER_ID` | yes | Phone number id |
| `WHATSAPP_VERIFY_TOKEN` | yes | Webhook verify challenge |
| `WHATSAPP_APP_SECRET` | recommended | Enables `X-Hub-Signature-256` validation |
| `WHATSAPP_APP_ID` | optional | Needed if auto-registering callback URL |
| `WHATSAPP_AGENT_ID` | no | Defaults to POC default agent |

If token / phone number id missing → do not register live handlers as “must pass”; simulated path remains active.

---

## GET /whatsapp/webhook (verify)

PyWa (or equivalent) handles Meta’s subscription challenge.

| Condition | Result |
|-----------|--------|
| `hub.mode=subscribe` and verify token matches | `200` + raw `hub.challenge` |
| mismatch / missing | `403` |

---

## POST /whatsapp/webhook

Ack the messaging network immediately (`200`), then process asynchronously via the **same** conversation find-or-create + arq enqueue path as simulated inbound.

### Behavior

| Inbound kind | Action |
|--------------|--------|
| Text | Find-or-create by WhatsApp sender id as `wa_id`; insert customer inbox text; enqueue text job if `BOT_AUTO` |
| Button / list reply | Resolve open conversation; enqueue button job with option id |
| Duplicate `message_id` | Ignore (no second inbox row, no second job) |
| Invalid signature (secret configured) | `401`; no work scheduled |

### MUST

- Return network success without awaiting `run_async`
- Mark message read / typing indicator when the API supports it
- Deliver bot/operator outbound (text, buttons, list, location, media) through PyWa to the customer thread
- Resume pending choices from button taps as `function_response`, not invented user text

### MUST NOT

- Use `whatsapp:{phone}:{digits}` as ADK session id (conversation UUID remains session id)
- Invent a second agent host separate from TurnService

---

## Optional: POST /whatsapp/nudge

Proactive tip into an existing session **only** inside the customer-care window.

| Condition | Result |
|-----------|--------|
| Window open | Accepted; may schedule agent turn |
| Window closed | `409` conflict; no send |

Not required for go/no-go.

---

## Skip semantics

| Credentials | Automated tests | RESULTS WhatsApp row |
|-------------|-----------------|----------------------|
| Present | Live text + choice pass expected | `pass` / `fail` |
| Absent | Marked skipped | `skip` |

Templates, Flows, voice calls, and multi-tenant WABA credentials are out of contract scope.
