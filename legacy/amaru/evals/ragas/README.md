# Ragas: salud del RAG (Amaru)

Tablero de retrieve + generate naive contra un golden set. **No** pasa por el agente WhatsApp (sin BANT, HITL ni tool-calling). Juez: AI Studio (`GEMINI_API_KEY`), nunca Vertex.

API: el mismo patrón del [howto Ragas](https://docs.ragas.io/en/stable/howtos/applications/evaluate-and-improve-rag/): `Dataset` (dicts) → `@experiment()` → `ascore`. Métricas: Context Recall, Context Precision, Faithfulness. Juez: `llm_factory(..., provider="google")`. Empieza por el hello world. `run.py` es `NaiveRAG.query` + el experiment contra la KB cloud.

## Las tres métricas

| Métrica | Capa | Pregunta |
|---|---|---|
| Context recall | Retriever / chunking | ¿Los chunks tienen los hechos del `reference`? |
| Context precision | Retriever | ¿Los chunks son pertinentes o hay ruido? |
| Faithfulness | Generador | ¿La respuesta se inventa respecto al contexto? |

Cómo leer el tablero:

- recall bajo → retrieval / chunking / KB
- precision baja → ruido en el top-k
- recall alto + faithfulness baja → el generador alucina
- las tres altas → RAG sano **en ese golden set**

Correctness (pass/fail vs gold) **no** está en este tablero: no es una métrica RAG de collections.

Guion de la charla: [`talk.md`](./talk.md).

## Hello world (primera vez con Ragas)

Tres samples fijos en [`hello_world.json`](./hello_world.json): RAG sano, retriever enfermo (Chingaza con chunks de parapente), generador enfermo (inventa el precio GoPro). No llama a Supabase.

```bash
cd projects/agents/amaru
just eval-ragas-hello
```

`just eval-ragas-hello` copia `.env.prod` → `.env` y corre [`hello_world.py`](./hello_world.py). Solo hace falta `GEMINI_API_KEY`. Costo: segundos.

Directo:

```bash
uv run --extra ragas evals/ragas/hello_world.py
```

`just sync` instala el extra `ragas` en el `.venv` del proyecto.

## Eval contra la KB Amaru

Misma receta, 35 preguntas de [`dataset.json`](./dataset.json), retrieve real (`search-knowledge`, `k=4` pinneado; el default de `search_context` es 10).

Needs cloud Supabase in `.env.prod` (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`) plus `GEMINI_API_KEY`. The harness ignores `GOOGLE_GENAI_USE_VERTEXAI` from the agent profile.

```bash
cd projects/agents/amaru
just eval-ragas                 # default: semantic vs hybrid at k=4
just eval-ragas -- --limit 10   # smoke; the extra -- is for just, not argparse
just eval-ragas-ui              # http://127.0.0.1:5000
```

Para un **snapshot de salud** (un retriever, no un A/B):

```bash
just eval-ragas -- --modes hybrid
```

CSV: el backend Ragas `local/csv` escribe `evals/ragas/experiments/{mode}-{stamp}.csv`. MLflow (overlay): `evals/ragas/mlflow.db` (gitignored). After `just eval-ragas-ui`, open **http://127.0.0.1:5000/#/experiments/1** and the **Runs** table. **Overview > Usage is empty on purpose** — that tab is GenAI traces; this harness only logs metrics + CSV artifacts.

### Models (same `GEMINI_API_KEY`)

| Role | Model | Thinking |
|---|---|---|
| Generator (`run.py` only) | `gemini-3.5-flash-lite` | off |
| Judge | `gemini-3.5-flash` | off |

Edge embeddings for `search-knowledge` are billed on the **edge function** Gemini key, not this one.

Order of magnitude for the full KB run: ~35 questions ≈ unos cientos de llamadas del juez, about **$1–2**. Hello world is negligible. Start with `--limit 10` on `run.py`.

`query_kind` on `dataset.json` is a **question label** (`keyword` | `paraphrase` | `mixed`), not a search mode. `reference` is the ground truth for Context Recall and Context Precision.

## Nota: A/B semantic vs hybrid

`just eval-ragas` still defaults to both modes. That comparison is **not** the health dashboard.

If ranking is identical (same top-1 / Jaccard ≈ 1), do not read Ragas deltas of ~0.01 as a product win — that is judge noise. Overlap of `chunk_ids` is printed after the table. rag-debug in the CRM remains the qualitative chunk viewer.

## Out of scope

- Agent / ADK evals (`just eval-handoff`) — WhatsApp behavior, not chunk quality
- Vertex / ADC for this harness
- `searchType=fulltext`
- CI, synthetic Ragas testset generation, production MLflow
- DiscreteMetric / correctness (not a collections RAG metric)
