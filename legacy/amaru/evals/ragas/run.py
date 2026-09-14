"""Naive RAG A/B: search-knowledge → @experiment (same shape as the Ragas howto).

Uses AI Studio (`GEMINI_API_KEY`), never Vertex/ADC, never searchType=fulltext.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
import mlflow
import pandas as pd
from google import genai
from judge import (
    GENERATOR_MODEL,
    JUDGE_MODEL,
    build_judge,
    generate_complete,
    load_studio_key,
    score_rag,
)
from ragas import Dataset, experiment
from supabase import ClientOptions, create_client

SearchMode = Literal["semantic", "hybrid"]

DEFAULT_MATCH_COUNT = 4
ORG_SLUG_DEFAULT = "amaru"
ROW_CONCURRENCY = 4

HERE = Path(__file__).resolve().parent
EXPERIMENTS_DIR = HERE / "experiments"
MLFLOW_DB = HERE / "mlflow.db"

GENERATE_PROMPT = """Eres un asistente de Xperiencia. Responde SOLO con la información del contexto.
Si el contexto no alcanza para responder, di que no tienes esa información en la base de conocimiento.
No inventes precios, horarios ni detalles que no estén en el contexto.
Responde en español, de forma breve y concreta.

Pregunta:
{question}

Contexto:
{context}

Respuesta:"""

_sem = asyncio.Semaphore(ROW_CONCURRENCY)


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"error: missing {name} (just eval-ragas copies .env.prod → .env)"
        )
    return value


def parse_modes(raw: str) -> list[SearchMode]:
    modes: list[SearchMode] = []
    for part in raw.split(","):
        mode = part.strip().lower()
        if not mode:
            continue
        if mode not in {"semantic", "hybrid"}:
            raise SystemExit(f"error: unknown mode {mode!r}; allowed: semantic,hybrid")
        if mode not in modes:
            modes.append(mode)  # type: ignore[arg-type]
    if not modes:
        raise SystemExit("error: need at least one of semantic,hybrid")
    return modes


def load_dataset(path: Path, limit: int | None) -> Dataset:
    rows = json.loads(path.read_text(encoding="utf-8"))
    dataset = Dataset(name="amaru-gold", backend="local/csv", root_dir=str(HERE))
    for row in rows[:limit]:
        dataset.append(
            {
                "id": str(row["id"]),
                "question": str(row["question"]),
                "reference": str(row["reference"]),
                "query_kind": row["query_kind"],
            }
        )
    return dataset


def supabase_client():
    return create_client(
        _require("SUPABASE_URL"),
        _require("SUPABASE_SECRET_KEY"),
        options=ClientOptions(function_client_timeout=60),
    )


def get_organization_id(client: Any, slug: str) -> str:
    response = (
        client.table("organizations").select("id").eq("slug", slug).limit(1).execute()
    )
    org_id = (response.data or [{}])[0].get("id")
    if not org_id:
        raise RuntimeError(f"No organization found for slug={slug}")
    return org_id


class NaiveRAG:
    """Retrieve once (search-knowledge), then generate. Same idea as the Ragas RAG class."""

    def __init__(
        self,
        sb: Any,
        org_id: str,
        client: genai.Client,
        mode: SearchMode,
        match_count: int = DEFAULT_MATCH_COUNT,
    ):
        self.sb = sb
        self.org_id = org_id
        self.client = client
        self.mode = mode
        self.match_count = match_count

    def query(self, question: str) -> dict[str, Any]:
        try:
            raw = self.sb.functions.invoke(
                "search-knowledge",
                invoke_options={
                    "body": {
                        "organizationId": self.org_id,
                        "searchType": self.mode,
                        "query": question,
                        "matchCount": self.match_count,
                    },
                    "responseType": "json",
                },
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise RuntimeError(f"search-knowledge failed: {exc}") from exc
        hits = raw.get("results") if isinstance(raw, dict) else None
        if raw.get("error") if isinstance(raw, dict) else None:
            raise RuntimeError(str(raw["error"]))
        if not isinstance(hits, list):
            raise RuntimeError("search-knowledge returned an invalid results payload")

        contexts: list[str] = []
        chunk_ids: list[str] = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            content = hit.get("content")
            if isinstance(content, str) and content.strip():
                contexts.append(content)
            chunk_id = hit.get("id")
            if isinstance(chunk_id, str) and chunk_id:
                chunk_ids.append(chunk_id)

        context = "\n\n---\n\n".join(contexts) if contexts else "(sin resultados)"
        answer = generate_complete(
            self.client,
            GENERATOR_MODEL,
            GENERATE_PROMPT.format(question=question, context=context),
        )
        return {
            "answer": answer,
            "retrieved_contexts": contexts,
            "chunk_ids": chunk_ids,
        }


@experiment()
async def evaluate_rag(row: dict[str, Any], rag: NaiveRAG, llm) -> dict[str, Any]:
    async with _sem:
        rag_response = await asyncio.to_thread(rag.query, row["question"])
        scores = await score_rag(
            llm,
            user_input=row["question"],
            retrieved_contexts=rag_response["retrieved_contexts"],
            reference=row["reference"],
            response=rag_response["answer"],
        )
    return {
        **row,
        "mode": rag.mode,
        "response": rag_response["answer"],
        "n_retrieved": len(rag_response["retrieved_contexts"]),
        "chunk_ids": ";".join(rag_response["chunk_ids"]),
        **scores,
    }


def _mean(frame: pd.DataFrame, column: str) -> float:
    numeric = pd.to_numeric(frame[column], errors="coerce")
    if not isinstance(numeric, pd.Series):
        numeric = pd.Series(numeric)
    value = numeric.mean()
    if isinstance(value, (int, float)):
        return float(value)
    return float("nan")


def print_overlap(frames: dict[str, pd.DataFrame]) -> None:
    if set(frames) != {"semantic", "hybrid"}:
        return
    sem = frames["semantic"].set_index("id")
    hyb = frames["hybrid"].set_index("id")
    shared = sem.index.intersection(hyb.index)
    if shared.empty:
        return
    same_top1 = 0
    jaccards: list[float] = []
    differed: list[str] = []
    for qid in shared:
        a = [p for p in str(sem.loc[qid, "chunk_ids"]).split(";") if p]
        b = [p for p in str(hyb.loc[qid, "chunk_ids"]).split(";") if p]
        left, right = set(a), set(b)
        jaccards.append(
            1.0 if not left and not right else len(left & right) / len(left | right)
        )
        if (a[:1] or [""]) == (b[:1] or [""]):
            same_top1 += 1
        if a != b:
            differed.append(str(qid))
    n = len(shared)
    print("\nRetrieval overlap (semantic vs hybrid):")
    print(f"  set Jaccard:  {sum(jaccards) / n:.3f}")
    print(f"  same top-1:   {same_top1}/{n}")
    if differed:
        print(f"  differed:     {', '.join(differed[:12])}")
    else:
        print("  differed:     none — hybrid is a no-op on this k + dataset")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ragas A/B: search-knowledge semantic vs hybrid (Amaru cloud KB)."
    )
    parser.add_argument("--modes", default="semantic,hybrid")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--match-count", type=int, default=DEFAULT_MATCH_COUNT)
    parser.add_argument("--org-slug", default=ORG_SLUG_DEFAULT)
    parser.add_argument("--dataset", type=Path, default=HERE / "dataset.json")
    return parser.parse_args([a for a in sys.argv[1:] if a != "--"])


async def main() -> None:
    args = parse_args()
    modes = parse_modes(args.modes)
    api_key = load_studio_key()
    dataset = load_dataset(args.dataset, args.limit)
    print(
        f"Loaded {len(dataset)} questions from {args.dataset.name} "
        f"(modes={','.join(modes)}, k={args.match_count})"
    )
    print(f"Generator={GENERATOR_MODEL}  judge={JUDGE_MODEL}  backend=AI Studio")

    sb = supabase_client()
    org_id = get_organization_id(sb, args.org_slug)
    client = genai.Client(api_key=api_key)
    llm = build_judge(api_key)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    summaries: dict[str, dict[str, float]] = {}
    frames: dict[str, pd.DataFrame] = {}

    mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB}")
    mlflow.set_experiment("amaru-ragas-semantic-vs-hybrid")
    mlflow.set_experiment_tag("mlflow.experimentKind", "custom_model_development")

    for mode in modes:
        name = f"{mode}-{stamp}"
        print(f"\n=== {mode} ===", flush=True)
        results = await evaluate_rag.arun(
            dataset,
            name=name,
            rag=NaiveRAG(sb, org_id, client, mode, args.match_count),
            llm=llm,
        )
        df = results.to_pandas()
        csv_path = EXPERIMENTS_DIR / f"{name}.csv"
        metrics = {
            "context_recall": _mean(df, "context_recall"),
            "context_precision": _mean(df, "context_precision"),
            "faithfulness": _mean(df, "faithfulness"),
        }
        summaries[mode] = metrics
        frames[mode] = df
        with mlflow.start_run(run_name=mode):
            mlflow.log_params(
                {
                    "mode": mode,
                    "generator": GENERATOR_MODEL,
                    "judge": JUDGE_MODEL,
                    "match_count": args.match_count,
                }
            )
            mlflow.log_metrics(metrics)
            if csv_path.exists():
                mlflow.log_artifact(str(csv_path))
        print(f"  wrote {csv_path}")
        print("  " + "  ".join(f"{k}={v:.3f}" for k, v in metrics.items()))

    keys = ["context_recall", "context_precision", "faithfulness"]
    header = f"{'metric':<24}" + "".join(f"{m:>12}" for m in summaries)
    if len(summaries) == 2:
        header += f"{'delta':>12}"
    print("\n" + header)
    print("-" * len(header))
    mode_names = list(summaries)
    for key in keys:
        values = [summaries[m][key] for m in mode_names]
        line = f"{key:<24}" + "".join(f"{v:12.3f}" for v in values)
        if len(values) == 2:
            line += f"{values[1] - values[0]:12.3f}"
        print(line)

    print_overlap(frames)
    print(f"\nCSV: {EXPERIMENTS_DIR}")
    print("MLflow: just eval-ragas-ui  →  http://127.0.0.1:5000/#/experiments/1")


if __name__ == "__main__":
    asyncio.run(main())
