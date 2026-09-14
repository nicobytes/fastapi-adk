# Evaluation Datasets

## Spanish handoff suite (POC)

```bash
cd projects/agents/be-unique
ADK_DEV_MODE=true agents-cli eval generate \
  --dataset tests/eval/datasets/handoff-es-dataset.json \
  --output traces_handoff_es/
ADK_DEV_MODE=true agents-cli eval grade --traces traces_handoff_es/
```

Cases cover greeting, no handoff on turn 1, RAG precio Sucre, mid-funnel qualify,
handoff-ready + bridge, explicit human request, browsing without handoff, and
Cochabamba valuation without Bs 100.

## Running Evaluations (generic)

```bash
agents-cli eval generate
agents-cli eval grade
```

See [agents-cli evaluation guide](https://google.github.io/agents-cli/guide/evaluation/) for metrics and dataset schema.
