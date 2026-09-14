# RESULTS.md — Durable queue + ADK Runner go/no-go (Python / FastAPI)

**Date**: 2026-09-14  
**Spec**: `specs/001-python-adk-poc/`  
**Queue name**: `fastapi-adk-messages`

| Pregunta | Resultado | Evidencia |
|----------|-----------|-----------|
| ¿HTTP acka y arq corre el Runner? | **sí** | `tests/test_queue_ack.py` — ack < 100ms con turn 1.5s |
| ¿Job delayed sobrevive restart? | **sí** | `tests/test_queue_restart.py` — enqueue sin worker + reopen con worker |
| ¿3 textos → 1 run_async (buffer)? | **sí** | `tests/test_queue_buffer.py` — batch |
| ¿Follow-up si llegó texto durante el job? | **sí** | `tests/test_queue_buffer.py` — follow-up |
| ¿Otra conversación HTTP viva durante run? | **sí** | `tests/test_queue_isolation.py` — health + other inbound < 200ms |
| **¿Vale la pena el processor vs run en el POST?** | **sí** | A1+A4; A3 covered; retries configurados (`Retry` + max_tries=3) |
| ¿Retry tras throw en processor? | **sí** | `tests/test_queue_retry.py` — re-push buffer + Retry |
| ¿Pause Eve + clic = functionResponse **en job**? | **parcial** | Código en `AdkHost.resume` + `ask_choice` LongRunningFunctionTool; live Gemini pendiente de `GOOGLE_API_KEY` |
| ¿Pause sobrevive restart (session, no RAM)? | **diseño sí** | pending choice desde `session.events` (`find_pending_choice`) |
| ¿`conversations.id` = `session_id`? | **sí** | `tests/test_conversation_identity.py` |
| ¿HITL salta el Runner? | **sí** | `tests/test_hitl_skip.py` |
| ¿Operador entra a session sin LLM? | **implementado** | `TurnService.append_operator_reply` + `append_event`; live assert con key pendiente |
| ¿Inbox `messages` ≠ prompt history? | **sí** | dual-write + `tests/test_dual_write_history.py` |
| ¿Botones/listas/clic en `messages`? | **sí (botones/clic)** | `tests/test_channel_crm_mapping.py` + stray click |
| ¿Session result es gist, no Graph? | **sí (ask_choice)** | `return None` + `skip_summarization` |
| ¿Resume optionId + choice CRM? | **diseño sí** | `run_button_turn` escribe choice + resume function_response |
| ¿Inbox sin parsear session.events? | **sí** | `to_inbox()` |
| ¿Retry no duplica botones? | **sí** | `sent_tool_calls` + `tests/test_queue_ask_choice_idempotent.py` |
| ¿Pause no duplica texto+botones? | **sí** | `suppress_text_when_paused` en `AdkHost` |
| BuiltInPlanner / ContextCache | **N/A / no re-testeado** | fuera del camino de decisión de cola |
| **¿Go Runner+arq (un tenant, un agente)?** | **sí con condiciones** | Redis dedicado/queue name propio; SQLite stub; BUFFER_MS demo; worker in-process OK (A5 pass) |
| **¿Go port agentes especialistas?** | **no / más tarde** | lab `amaru_lite` opcional; skills+agenda out of scope |
| ¿Paridad Nest decision path? | **sí (cola + identidad + HITL + dual-write)** | mismos criterios A1–A5, C, D, F, G |
| ¿WhatsApp live text+choice? | **skip / listo para creds** | PyWa montado si env; `tests/test_whatsapp_dedupe.py`; sin creds = skip |

## Condiciones / notas

1. **Redis compartido**: usar queue name `fastapi-adk-messages` (no compartir con Nest).
2. **Worker**: embebido en lifespan por defecto; `EMBED_WORKER=false` + `arq app.queue.worker.WorkerSettings` si hace falta.
3. Tests live Gemini requieren `GOOGLE_API_KEY`.
4. Path de decisión: `POST /inbound` con `waId`. Legacy `sessionId` sync sigue para demos.

## Criterio

- **Go teórico (canal + cola + runner):** A1–A5, C, D, G, I (parcial Eve live) → **sí con condiciones** arriba.
- **No-go port agentes producción:** se mantiene.
