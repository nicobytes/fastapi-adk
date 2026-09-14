"""Local LLM-as-judge for `agents-cli eval grade`, wired in from
tests/eval/eval_config.yaml (`custom_function_file: metrics.py`).

Scores the agent's final response 1-5 via google-genai. For Amaru handoff
evals, the case `reference` describes expected bridge behavior and turn gates.
"""

from google import genai
from google.genai import types
from pydantic import BaseModel


class _Verdict(BaseModel):
    score: int  # 1-5
    explanation: str


def evaluate(instance):
    reference = instance.get("reference")
    rubric = (
        "Grade Amaru (Xperiencia WhatsApp guide) on a 1-5 scale (1 poor, 5 "
        "excellent). Check: warm Spanish (colombian-friendly, not corporate), "
        "no invented prices/dates without search_context, and whether behavior "
        "matches the expected rubric. On handoff success the final user-visible "
        "text should be a short bridge to a human advisor only — not more sales "
        "copy, payment links, or reservation URLs. Penalize handoff on the "
        "user's first message unless they explicitly asked for a human. Penalize "
        "handoff when budget is Insufficient. On handoff success the bridge may "
        "personalize with plan/date from chat history but must follow the spirit "
        "of the configured bridge example (connecting to a human advisor); penalize "
        "continued selling, payment/reservation links, or denying that a human will follow up."
    )
    if reference:
        rubric += (
            " Follow the Expected Answer rubric below as the primary grading "
            "criteria; penalize disagreement with it."
        )
    prompt = (
        f"You are an expert QA evaluator for a WhatsApp travel/experience bot. "
        f"{rubric}\n"
        f"User Prompt: {instance.get('prompt', '')}\n"
        f"Final Response: {instance.get('response', '')}\n"
    )
    if reference:
        prompt += f"Expected Answer (ground truth / rubric): {reference}\n"
    prompt += f"Full Agent Trace: {instance.get('agent_data', '')}\n"

    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=_Verdict,
        ),
    )
    verdict = response.parsed
    if verdict is None:
        return {"score": 0, "explanation": response.text or ""}
    return {"score": max(1, min(5, verdict.score)), "explanation": verdict.explanation}
