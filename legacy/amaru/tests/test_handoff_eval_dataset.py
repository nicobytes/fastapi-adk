"""Sanity checks for the HITL handoff eval suite (no live LLM calls)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import ClassVar

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_DATASET = _TESTS_DIR / "eval" / "datasets" / "handoff-es-dataset.json"
_SITECUSTOMIZE = _TESTS_DIR / "eval" / "path_hooks" / "sitecustomize.py"

_EXPECTED_CASE_IDS = {
    "es_greeting_no_handoff",
    "es_no_handoff_turn1_booking",
    "es_browsing_plans",
    "es_whale_watching_short_reply",
    "es_whale_watching_bant_polluted_history",
    "es_mid_funnel_no_date",
    "es_handoff_plan_and_date",
    "es_explicit_human",
    "es_no_payment_links",
    "es_insufficient_budget",
    "es_cocuy_date_triggers",
    "es_pick_date_from_list_no_handoff",
    "es_date_plus_logistics_no_handoff",
    "es_availability_window_no_handoff",
    "es_want_reserve_then_pick_date_no_handoff",
    "es_yes_after_reserve_ask",
    "es_no_published_date_offer_custom",
    "es_accept_custom_group_handoff",
    "es_high_score_no_confirm_no_handoff",
    "es_disability_access_handoff",
}


def test_handoff_dataset_cases_present() -> None:
    data = json.loads(_DATASET.read_text(encoding="utf-8"))
    cases = data["eval_cases"]
    ids = {c["eval_case_id"] for c in cases}
    assert ids == _EXPECTED_CASE_IDS
    for case in cases:
        ref = case.get("reference", {}).get("response", {}).get("parts", [])
        assert ref and ref[0].get("text"), case["eval_case_id"]
        assert "prompt" in case or "agent_data" in case


def test_vertex_agent_config_patch_accepts_callable_instruction() -> None:
    """sitecustomize must coerce callable instruction for Vertex AgentConfig."""
    pytest.importorskip("vertexai")

    spec = importlib.util.spec_from_file_location(
        "amaru_eval_sitecustomize", _SITECUSTOMIZE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._patch_agent_config()

    from vertexai._genai.types.evals import AgentConfig

    class _FakeAgent:
        name = "amaru"
        description = "test"
        instruction = staticmethod(lambda ctx: "hello")  # callable
        tools: ClassVar[list] = []
        sub_agents: ClassVar[list] = []

    cfg = AgentConfig.from_agent(_FakeAgent())
    assert cfg.agent_id == "amaru"
    assert isinstance(cfg.instruction, str)
