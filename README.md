# fastapi-adk

POC: FastAPI + Google ADK (Python) with a **durable arq/Redis decision path**,
parity with [nestjs-adk](https://github.com/nicobytes/nestjs-adk). Live WhatsApp via [PyWa](https://pywa.readthedocs.io/en/latest/) when credentials are set.

## Decision path (go/no-go)

Requires **Redis** (`REDIS_URL`, default `redis://127.0.0.1:6379`). Queue name: `fastapi-adk-messages`.

```bash
docker run --rm -p 6379:6379 redis:7
cp .env.example .env   # optional GOOGLE_API_KEY / WhatsApp
uv sync --group dev
uv run pytest
uv run fastapi dev --app app.main:app
# or: uv run uvicorn app.main:app --reload
```

```bash
curl -s localhost:8000/inbound -H 'content-type: application/json' \
  -d '{"waId":"5215512345678","text":"hola"}'
# → { "conversationId": "<uuid>", "status": "BOT_AUTO", "accepted": true }

curl -s localhost:8000/inbound/interactive -H 'content-type: application/json' \
  -d '{"conversationId":"<uuid>","buttonId":"b"}'

curl -s localhost:8000/conversations/<uuid>/handoff -X POST
curl -s localhost:8000/operator/reply -H 'content-type: application/json' \
  -d '{"conversationId":"<uuid>","text":"el precio es 100"}'
curl -s localhost:8000/health
```

Verdict table: **RESULTS.md**. Spec/plan/tasks: `specs/001-python-adk-poc/`.

Live Gemini tests skip unless `GOOGLE_API_KEY` is set. `/whatsapp/webhook` is mounted only when WhatsApp env vars are present; simulated `/inbound` remains the architecture decision path.

## WhatsApp (PyWa)

Set `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` (and ideally `WHATSAPP_APP_SECRET`). Webhook: `/whatsapp/webhook`.

## Worker

By default the arq worker is **embedded** in the FastAPI lifespan. To run separately:

```bash
# EMBED_WORKER=false on the API process
uv run arq app.queue.worker.WorkerSettings
```
