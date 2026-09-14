# be-unique

WhatsApp ADK agent for Be Unique: Sofía (BaseAgent orchestrator + sub-agents) — qualify, HITL bridge, RAG, agenda.

See [`AGENTS.md`](./AGENTS.md).

## Layout

```
app/
├── agent.py           # root Sofía + App
├── instructions/      # personality/instructions/session + load_agent_instructions
├── callbacks.py
└── tools/             # search, scheduling, qualify/handoff
tests/
└── eval/datasets/handoff-es-dataset.json
```

## Quick start

```bash
cd projects/agents/be-unique
cp .env.example .env.local   # just serve
cp .env.example .env.prod    # just deploy
just sync && just serve
```
