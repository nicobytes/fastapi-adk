# Evaluation Datasets

## Spanish handoff suite (HITL)

Covers greeting, no handoff on turn 1, browsing plans, mid-funnel without date,
plan+listed-departure confirmation + bridge, explicit human request, no payment
links after handoff, insufficient budget (no handoff), date-mention without
confirmation (no handoff), list pick / logistics / availability window (no
handoff), early “quiero reservar” then pick a date (no handoff), yes after
“¿reservamos esa?”, custom-group offer vs accept, high score without confirm
(no handoff), disability/accessibility handoff (incl. turn 1), and Shape C
(qualifier BANT JSON pre-seeded in session history).

Deterministic gate: `forbidden_output` metric (score 0 if handoff/BANT/internal
jargon leaks to the user). Runs alongside the LLM judge (`custom_response_quality`).

```bash
cd projects/agents/amaru
just eval-handoff         # generate traces
just eval-handoff-grade   # grade with custom_response_quality (metrics.py)
```

Or manually:

```bash
ADK_DEV_MODE=true agents-cli eval generate \
  --dataset tests/eval/datasets/handoff-es-dataset.json \
  --output traces_handoff_es/
ADK_DEV_MODE=true agents-cli eval grade --traces traces_handoff_es/
```

`ADK_DEV_MODE=true` is required so handoff does not fail when the eval session
id has no matching Supabase conversation row.

**Auth:** `eval generate` needs working Application Default Credentials
(`gcloud auth application-default login`) because the agent model runs on Vertex.

**Callable instruction patch:** `just eval-handoff` sets
`PYTHONPATH=tests/eval/path_hooks` so `sitecustomize.py` can coerce Amaru's
dynamic `build_instruction` for Vertex `AgentConfig` (metadata-only).

## Running Evaluations (generic)

```bash
agents-cli eval generate
agents-cli eval grade
```

### Custom Dataset
```bash
agents-cli eval generate --dataset tests/eval/datasets/custom-dataset.json --output custom_traces/
agents-cli eval grade --metrics general_quality --traces custom_traces/
```

## Dataset Format

Each dataset file follows the Gemini Enterprise Agent Platform Evaluation
dataset format. An eval case may use **either** of two shapes — both are
valid input to `agents-cli eval generate`:

**Shape A — single-prompt case:**

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "prompt": {
        "role": "user",
        "parts": [{"text": "User message"}]
      },
      "reference": {
        "response": {
          "role": "model",
          "parts": [{"text": "Rubric for the LLM judge (expected tools / behavior)."}]
        }
      }
    }
  ]
}
```

**Shape B — continued-conversation case (the "N+1" pattern):**
The case carries prior turns in `agent_data` and the last turn ends with a
user message; `eval generate` appends the next agent response. Use
`"author": "amaru"` for prior model turns.

**Shape C — polluted internal history (qualifier leak regression):**
Same as Shape B, but seed a prior-turn `qualifier` event whose `content` is
BANT JSON between the last model turn and the final user message. This
reproduces session pollution when the customer LLM must ignore internal JSON.
Cases: `es_whale_watching_bant_polluted_history`. Pair with `forbidden_output`
(score 0 on handoff/BANT/meta-commentary leaks).

## Discovering Metrics

```bash
agents-cli eval metric list
```

## Beyond Generate and Grade

- `agents-cli eval compare BASE CAND` — diff two grade-results files
- `agents-cli eval analyze RESULTS` — cluster failure modes
- `agents-cli eval optimize` — auto-tune prompts using eval data

See the [Evaluation Guide](https://google.github.io/agents-cli/guide/evaluation/).
