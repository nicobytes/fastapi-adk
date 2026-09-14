"""Hello world: @experiment on 3 fixed samples. No Supabase.

Needs GEMINI_API_KEY (just eval-ragas-hello copies .env.prod → .env).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from judge import JUDGE_MODEL, build_judge, load_studio_key, score_rag
from ragas import Dataset, experiment

HERE = Path(__file__).resolve().parent
SAMPLES_PATH = HERE / "hello_world.json"


def load_dataset() -> Dataset:
    rows = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    dataset = Dataset(name="hello-world", backend="local/csv", root_dir=str(HERE))
    for row in rows:
        dataset.append(row)
    return dataset


@experiment()
async def evaluate_hello(row: dict[str, Any], llm) -> dict[str, Any]:
    scores = await score_rag(
        llm,
        user_input=row["user_input"],
        retrieved_contexts=row["retrieved_contexts"],
        reference=row["reference"],
        response=row["response"],
    )
    return {**row, **scores}


async def main() -> None:
    llm = build_judge(load_studio_key())
    dataset = load_dataset()
    print(f"Hello world Ragas: {len(dataset)} samples from {SAMPLES_PATH.name}")
    print(f"Judge={JUDGE_MODEL}  backend=AI Studio  (no retrieve, no agent)")
    print("Scoring context recall, precision, faithfulness…", flush=True)

    results = await evaluate_hello.arun(dataset, name="hello-world", llm=llm)
    order = {row["id"]: i for i, row in enumerate(dataset)}
    rows = sorted(results, key=lambda row: order.get(row["id"], 0))

    header = f"{'id':<36}{'label':<22}{'recall':>8}{'prec':>8}{'faith':>8}"
    print("\n" + header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['id']:<36}{row['label']:<22}"
            f"{row['context_recall']:8.2f}{row['context_precision']:8.2f}"
            f"{row['faithfulness']:8.2f}"
        )
    n = len(rows)
    print("-" * len(header))
    print(
        f"{'mean':<36}{'':<22}"
        f"{sum(r['context_recall'] for r in rows) / n:8.2f}"
        f"{sum(r['context_precision'] for r in rows) / n:8.2f}"
        f"{sum(r['faithfulness'] for r in rows) / n:8.2f}"
    )
    print(
        "\nHow to read: recall/precision = retriever; "
        "faithfulness = generator vs context."
    )
    print("Next: evals/ragas/run.py scores the real Amaru KB (just eval-ragas).")


if __name__ == "__main__":
    asyncio.run(main())
