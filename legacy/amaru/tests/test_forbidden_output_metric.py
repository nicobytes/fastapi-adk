"""Tests for deterministic forbidden_output eval metric."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_EVAL_DIR = Path(__file__).resolve().parent / "eval"
_FORBIDDEN_METRIC = _EVAL_DIR / "forbidden_output.py"


def _load_forbidden_evaluate():
    spec = importlib.util.spec_from_file_location(
        "amaru_forbidden_output_metric", _FORBIDDEN_METRIC
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate


def test_forbidden_output_metric_fails_on_leaked_meta_commentary() -> None:
    evaluate = _load_forbidden_evaluate()
    result = evaluate(
        {
            "response": (
                "Dado que el último mensaje del usuario fue puramente informativo "
                "(ejemplo de handoff y estado interno), esperaré su próxima "
                "intervención conversacional."
            )
        }
    )
    assert result["score"] == 0
    assert "handoff" in result["explanation"]


def test_forbidden_output_metric_passes_on_normal_reply() -> None:
    evaluate = _load_forbidden_evaluate()
    result = evaluate(
        {
            "response": (
                "¡Qué plan tan chévere! El avistamiento de ballenas en Nuquí "
                "es una experiencia increíble. ¿Te cuento qué incluye?"
            )
        }
    )
    assert result["score"] == 1
