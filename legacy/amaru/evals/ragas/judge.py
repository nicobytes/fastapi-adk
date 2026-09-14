"""Judge + generator for the Ragas harness (AI Studio, never Vertex)."""

from __future__ import annotations

import os
from pathlib import Path

import instructor
from dotenv import load_dotenv
from google import genai
from google.genai import types
from ragas.llms import llm_factory
from ragas.llms.base import InstructorBaseRagasLLM, InstructorLLM
from ragas.metrics.collections import (
    ContextPrecisionWithReference,
    ContextRecall,
    Faithfulness,
)

JUDGE_MODEL = "gemini-3.5-flash"
GENERATOR_MODEL = "gemini-3.5-flash-lite"

AMARU_ROOT = Path(__file__).resolve().parent.parent.parent


def load_studio_key() -> str:
    load_dotenv(AMARU_ROOT / ".env", override=False)
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
    api_key = (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )
    if not api_key:
        raise SystemExit("error: missing GEMINI_API_KEY (or GOOGLE_API_KEY) in .env")
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    return api_key


def build_judge(api_key: str) -> InstructorBaseRagasLLM:
    client = genai.Client(api_key=api_key)
    llm = llm_factory(JUDGE_MODEL, provider="google", client=client)
    if getattr(llm, "is_async", False):
        return llm
    patched = instructor.from_genai(client, use_async=True, model=JUDGE_MODEL)
    return InstructorLLM(client=patched, model=JUDGE_MODEL, provider="google")


def generate_complete(client: genai.Client, model: str, prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except Exception:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0),
        )
    return (response.text or "").strip() or "(vacío)"


async def score_rag(
    llm: InstructorBaseRagasLLM,
    *,
    user_input: str,
    retrieved_contexts: list[str],
    reference: str,
    response: str,
) -> dict[str, float]:
    contexts = retrieved_contexts or [""]
    recall = await ContextRecall(llm=llm).ascore(
        user_input=user_input,
        retrieved_contexts=contexts,
        reference=reference,
    )
    precision = await ContextPrecisionWithReference(llm=llm).ascore(
        user_input=user_input,
        reference=reference,
        retrieved_contexts=contexts,
    )
    faith = await Faithfulness(llm=llm).ascore(
        user_input=user_input,
        response=response,
        retrieved_contexts=contexts,
    )
    return {
        "context_recall": float(recall.value),
        "context_precision": float(precision.value),
        "faithfulness": float(faith.value),
    }
