"""Local LLM-as-judge for `agents-cli eval grade`, wired in from
tests/eval/eval_config.yaml (`custom_function_file: metrics.py`).

Scores the agent's final response 1-5 via google-genai. For Be Unique handoff
evals, the case `reference` describes expected tool use and bridge behavior.
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
        "Grade Sofía (Be Unique Clínica Estética WhatsApp assistant) on a 1-5 "
        "scale (1 poor, 5 excellent). Check: Spanish with usted, no invented "
        "prices, correct Sucre vs Cochabamba policy, and whether tools were used "
        "as expected. Critical tools: load_skill / load_skill_resource (catalog "
        "facts), list_available_days, book_appointment, send_sede_location. "
        "Customer must not call search_context. Handoff tools "
        "(submit_lead_qualification, request_human_handoff) are not on Sofía. "
        "On handoff success the final user-visible text "
        "should be a short bridge to a human advisor, not more sales copy. "
        "Penalize calling request_human_handoff on the user's first message "
        "unless they explicitly asked for a human."
    )
    if reference:
        rubric += (
            " Follow the Expected Answer rubric below as the primary grading "
            "criteria; penalize disagreement with it."
        )
    prompt = (
        f"You are an expert QA evaluator for a WhatsApp clinic bot. {rubric}\n"
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
