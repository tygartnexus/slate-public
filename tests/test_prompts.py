"""Prompt contract tests."""

from __future__ import annotations

from slate.manifest import Manifest
from slate.prompts import build_frame_analysis_prompt
from slate.response_quality import REQUIRED_SECTION_KEYS


def test_frame_analysis_prompt_requires_response_quality_sections() -> None:
    prompt = build_frame_analysis_prompt(Manifest(shot_id="x"))
    assert "AI RESPONSE QUALITY CONTRACT" in prompt
    assert "response_quality" in prompt
    assert "Do not invent facts" in prompt
    for key in REQUIRED_SECTION_KEYS:
        assert f'"{key}"' in prompt
