from __future__ import annotations

"""Minimal stubs for live Eve tests — skip without GOOGLE_API_KEY."""

import pytest

from tests.has_key import has_gemini_key

pytestmark = pytest.mark.skipif(not has_gemini_key(), reason="GOOGLE_API_KEY not set")


@pytest.mark.asyncio
async def test_pauses_on_ask_choice_in_a_queue_job_and_resumes_with_function_response():
    pytest.skip("Requires live Gemini + scripted ask_choice prompt; run manually with GOOGLE_API_KEY")


@pytest.mark.asyncio
async def test_resumes_a_paused_choice_after_process_restart():
    pytest.skip("Requires live Gemini; pending choice from session.events is covered by unit design")


@pytest.mark.asyncio
async def test_does_not_send_extra_text_when_ask_choice_pauses():
    pytest.skip("Covered by AdkHost.suppress_text_when_paused; live assert needs Gemini")
