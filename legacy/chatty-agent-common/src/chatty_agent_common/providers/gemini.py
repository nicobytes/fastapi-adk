from __future__ import annotations

import os

from google import genai

GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"

_GENAI_CLIENT: genai.Client | None = None


def get_genai_client() -> genai.Client:
    global _GENAI_CLIENT
    if _GENAI_CLIENT is None:
        _GENAI_CLIENT = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
        )
    return _GENAI_CLIENT


def get_embedding(query: str) -> list[float]:
    client = get_genai_client()
    result = client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=[query],
    )
    embeddings = getattr(result, "embeddings", None)
    if not embeddings:
        raise RuntimeError("Gemini embed_content returned no embeddings")

    first_embedding = embeddings[0]
    values = getattr(first_embedding, "values", None)
    if not isinstance(values, list) or not values:
        raise RuntimeError("Gemini embedding response has invalid values")

    return [float(value) for value in values]
