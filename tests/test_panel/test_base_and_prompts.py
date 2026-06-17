"""Edge-case coverage for the persona run helper, prompt scaffolding, and the
ensemble's lazy client construction.

All Claude interaction goes through the ``FakeClaudeClient`` fixture from the
shared conftest — no real SDK, no key, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slate.frames import list_frames
from slate.manifest import Manifest
from slate.panel.personas.base import (
    _clamp_severity,
    _parse_persona_json,
    run_persona,
)
from slate.panel.prompts import build_persona_prompt
from slate.verdict import SignalFailure, Verdict, VerdictStatus
from tests.conftest import FakeClaudeClient


def _quality() -> dict[str, object]:
    return {
        "facts": ["Persona reviewed sampled frames."],
        "assumptions": ["Manifest is accurate."],
        "unknowns": ["Unsampled frames."],
        "confidence_score": 0.76,
        "evidence": ["frame review"],
        "risks": ["Could miss between-frame issues."],
        "counterarguments": ["The sampled frame may be representative."],
        "recommendation": "Continue review.",
        "tradeoffs": ["More samples cost time."],
        "what_would_change_recommendation": ["A later frame shows a blocker."],
    }

# ---------------------------------------------------------------------------
# _clamp_severity (base.py 131-138)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("critical", "critical"),
        ("CRITICAL", "critical"),
        ("high", "high"),
        ("  High  ", "high"),
        ("low", "low"),
        ("medium", "medium"),
        ("bogus", "medium"),  # unknown -> medium
        (None, "medium"),  # missing -> medium
        (3, "medium"),  # non-string -> medium
    ],
)
def test_clamp_severity(raw: object, expected: str) -> None:
    assert _clamp_severity(raw) == expected


# ---------------------------------------------------------------------------
# _parse_persona_json (base.py 117-127)
# ---------------------------------------------------------------------------


def test_parse_persona_json_extracts_embedded_object() -> None:
    """Prose around a JSON object -> the object is sliced out (base.py line 120)."""
    text = 'Sure! Here is my answer: {"publish_ready": true, "summary": "ok"} -- done.'
    parsed = _parse_persona_json(text)
    assert parsed is not None
    assert parsed["publish_ready"] is True
    assert parsed["summary"] == "ok"


def test_parse_persona_json_rejects_non_object_json() -> None:
    """Valid JSON that is a list (not an object) -> None (base.py line 126)."""
    assert _parse_persona_json("[1, 2, 3]") is None


def test_parse_persona_json_rejects_unparseable() -> None:
    assert _parse_persona_json("not json at all") is None


def test_parse_persona_json_plain_object() -> None:
    assert _parse_persona_json('{"a": 1}') == {"a": 1}


# ---------------------------------------------------------------------------
# run_persona: per_frame_notes filtering (base.py 99-102)
# ---------------------------------------------------------------------------


def test_run_persona_filters_non_string_per_frame_notes(
    sample_manifest: Manifest, passing_core_verdict: Verdict, frames_dir: Path
) -> None:
    """Only str->str per-frame notes survive; other key/value types are dropped."""
    response = json.dumps(
        {
            "publish_ready": True,
            "summary": "ok",
            "flags": [],
            "per_frame_notes": {
                "frame_0000.png": "looks good",
                "frame_0002.png": 123,
                "frame_0004.png": "also good",
            },
            "response_quality": _quality(),
        }
    )
    client = FakeClaudeClient(response_text=response)
    frames = list_frames(frames_dir)
    result = run_persona(
        name="director",
        identity="id",
        criteria=["c1"],
        frames=frames,
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert result.ok
    # The int-valued note is filtered out; the two string notes are kept.
    assert result.per_frame_notes == {
        "frame_0000.png": "looks good",
        "frame_0004.png": "also good",
    }


def test_run_persona_ignores_non_dict_per_frame_notes(
    sample_manifest: Manifest, passing_core_verdict: Verdict, frames_dir: Path
) -> None:
    response = json.dumps(
        {
            "publish_ready": True,
            "summary": "ok",
            "flags": [],
            "per_frame_notes": "not a dict",
            "response_quality": _quality(),
        }
    )
    client = FakeClaudeClient(response_text=response)
    result = run_persona(
        name="director",
        identity="id",
        criteria=["c1"],
        frames=list_frames(frames_dir),
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert result.per_frame_notes == {}


def test_run_persona_skips_non_dict_flags(
    sample_manifest: Manifest, passing_core_verdict: Verdict, frames_dir: Path
) -> None:
    """Flag entries that are not dicts are ignored; the dict one is parsed."""
    response = json.dumps(
        {
            "publish_ready": False,
            "summary": "blocks",
            "flags": [
                "a stray string",
                {
                    "category": "lighting",
                    "severity": "high",
                    "frame": 7,
                    "description": "too dark",
                },
            ],
            "response_quality": _quality(),
        }
    )
    client = FakeClaudeClient(response_text=response)
    result = run_persona(
        name="director",
        identity="id",
        criteria=["c1"],
        frames=list_frames(frames_dir),
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert len(result.flags) == 1
    flag = result.flags[0]
    assert flag.category == "lighting"
    assert flag.severity == "high"
    assert flag.frame is None  # non-string frame coerced to None
    assert flag.description == "too dark"


def test_run_persona_rejects_missing_response_quality(
    sample_manifest: Manifest, passing_core_verdict: Verdict, frames_dir: Path
) -> None:
    response = '{"publish_ready": true, "summary": "ok", "flags": [], "per_frame_notes": {}}'
    client = FakeClaudeClient(response_text=response)
    result = run_persona(
        name="director",
        identity="id",
        criteria=["c1"],
        frames=list_frames(frames_dir),
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert not result.ok
    assert result.publish_ready is False
    assert "response_quality" in (result.error or "")
    assert result.response_quality is not None
    assert result.response_quality.evidence == []


def test_run_persona_rejects_invalid_response_quality(
    sample_manifest: Manifest, passing_core_verdict: Verdict, frames_dir: Path
) -> None:
    response = json.dumps(
        {
            "publish_ready": True,
            "summary": "ok",
            "flags": [],
            "per_frame_notes": {},
            "response_quality": {
                **_quality(),
                "recommendation": ["not a string"],
            },
        }
    )
    client = FakeClaudeClient(response_text=response)
    result = run_persona(
        name="director",
        identity="id",
        criteria=["c1"],
        frames=list_frames(frames_dir),
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert not result.ok
    assert result.summary == "(persona returned invalid response_quality)"
    assert result.error == "persona JSON has invalid response_quality object"


# ---------------------------------------------------------------------------
# build_persona_prompt: failures summary branch (prompts.py 113-119)
# ---------------------------------------------------------------------------


def _verdict_with_failures(n: int) -> Verdict:
    failures = [
        SignalFailure(
            signal=f"sig_{i}",
            value=f"v{i}",
            frame=f"frame_{i:04d}.png",
            provider="gemma",
            model="gemma4:latest",
            description="d",
        )
        for i in range(n)
    ]
    return Verdict(
        status=VerdictStatus.FAIL,
        shot_id="s",
        slate_version="0.1.0",
        started_at="2026-05-20T00:00:00Z",
        finished_at="2026-05-20T00:00:05Z",
        duration_seconds=5.0,
        providers_consulted=["gemma"],
        frames_analyzed=["frame_0000.png"],
        failures=failures,
        frame_analyses=[],
        quality_scores_aggregated={},
    )


def test_prompt_summarizes_failures_when_present(sample_manifest: Manifest) -> None:
    """A verdict with a few failures lists each one (prompts.py 113-116)."""
    verdict = _verdict_with_failures(3)
    prompt = build_persona_prompt(
        identity="You are a director.",
        criteria=["composition"],
        frame_paths=[Path("frame_0000.png")],
        manifest=sample_manifest,
        core_verdict=verdict,
    )
    assert "3 failure(s)" in prompt
    assert "[sig_0] frame_0000.png: v0" in prompt
    assert "and 3 more" not in prompt
    assert "response_quality" in prompt
    assert "Do not invent facts" in prompt


def test_prompt_truncates_failure_list_over_five(sample_manifest: Manifest) -> None:
    """More than 5 failures -> only 5 shown plus an 'and N more' line
    (prompts.py 117-118)."""
    verdict = _verdict_with_failures(8)
    prompt = build_persona_prompt(
        identity="You are a director.",
        criteria=["composition"],
        frame_paths=[Path("frame_0000.png")],
        manifest=sample_manifest,
        core_verdict=verdict,
    )
    assert "8 failure(s)" in prompt
    assert "and 3 more" in prompt  # 8 - 5 = 3
    # Only the first five are enumerated.
    assert "[sig_4]" in prompt
    assert "[sig_5]" not in prompt


def test_prompt_no_failures_says_no_signal_failures(
    sample_manifest: Manifest, passing_core_verdict: Verdict
) -> None:
    prompt = build_persona_prompt(
        identity="You are a director.",
        criteria=["composition"],
        frame_paths=[Path("frame_0000.png")],
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
    )
    assert "no signal failures" in prompt
