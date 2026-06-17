"""Verdict engine tests — uses FakeProvider so no Ollama / NVIDIA needed."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from slate.engine import _as_bool, _as_number, evaluate_frame_signals, verify
from slate.manifest import ExpectedCharacter, Manifest, QualityThresholds
from slate.providers.base import ProviderResult
from slate.verdict import VerdictStatus

# Imported through conftest.py
from tests.conftest import FakeProvider


def test_all_passing_signals_yield_pass(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    provider = FakeProvider(response_signals=passing_signals)
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[provider])
    assert verdict.status == VerdictStatus.PASS
    assert verdict.failures == []
    assert len(verdict.frame_analyses) == 3  # first/mid/last default
    assert provider.calls and len(provider.calls) == 3
    assert verdict.response_quality is not None
    assert verdict.response_quality.confidence_score > 0
    assert verdict.response_quality.assumptions
    assert verdict.response_quality.tradeoffs
    assert not any("response_quality" in item for item in verdict.response_quality.unknowns)


def test_missing_response_quality_yields_indeterminate(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    signals = dict(passing_signals)
    signals.pop("response_quality")
    provider = FakeProvider(response_signals=signals)
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[provider])
    assert verdict.status == VerdictStatus.INDETERMINATE
    assert any(f.signal == "__response_quality_missing__" for f in verdict.failures)
    assert verdict.response_quality is not None
    assert any("response_quality" in item for item in verdict.response_quality.unknowns)


def test_lying_horizontal_fails(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    bad = passing_signals | {"character_orientation": "lying_horizontal"}
    provider = FakeProvider(response_signals=bad)
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[provider])
    assert verdict.status == VerdictStatus.FAIL
    signals_hit = {f.signal for f in verdict.failures}
    assert "character_orientation" in signals_hit


def test_debug_or_broken_fails(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    bad = passing_signals | {"debug_quality_or_broken": True}
    provider = FakeProvider(response_signals=bad)
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[provider])
    assert verdict.status == VerdictStatus.FAIL
    assert any(f.signal == "debug_quality_or_broken" for f in verdict.failures)


def test_quality_below_threshold_fails(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    bad = passing_signals | {"lighting_quality": 1}
    provider = FakeProvider(response_signals=bad)
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[provider])
    assert verdict.status == VerdictStatus.FAIL
    assert any(f.signal == "lighting_quality" for f in verdict.failures)


def test_provider_error_yields_indeterminate_when_no_content_failures(
    sample_manifest: Manifest,
    frames_dir: Path,
) -> None:
    provider = FakeProvider(response_signals={}, error="ollama: connection refused")
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[provider])
    assert verdict.status == VerdictStatus.INDETERMINATE


def test_content_failure_dominates_provider_error(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    # One provider errors, another returns a content failure → FAIL (not INDETERMINATE).
    p1 = FakeProvider(label="bad", response_signals={}, error="ollama: connection refused")
    p2 = FakeProvider(
        label="good",
        response_signals=passing_signals | {"character_orientation": "t_pose"},
    )
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[p1, p2])
    assert verdict.status == VerdictStatus.FAIL


def test_multi_provider_quorum(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    """Two providers both pass → PASS; failures come from whichever provider flags them."""
    p1 = FakeProvider(label="gemma", response_signals=passing_signals)
    p2 = FakeProvider(label="nvidia-primary", response_signals=passing_signals)
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[p1, p2])
    assert verdict.status == VerdictStatus.PASS
    assert set(verdict.providers_consulted) == {"gemma", "nvidia-primary"}
    # 3 sampled frames * 2 providers = 6 analyses
    assert len(verdict.frame_analyses) == 6


def test_quality_scores_aggregated_across_frames(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    provider = FakeProvider(response_signals=passing_signals)
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[provider])
    assert "lighting_quality" in verdict.quality_scores_aggregated
    # passing_signals has lighting_quality=4; mean across 3 frames stays at 4.0
    assert verdict.quality_scores_aggregated["lighting_quality"] == 4.0


def test_frame_analysis_keeps_provider_response_quality(
    sample_manifest: Manifest,
    frames_dir: Path,
    passing_signals: dict[str, Any],
) -> None:
    signals = passing_signals | {
        "response_quality": {
            "facts": ["The character is visible."],
            "assumptions": ["The sampled frame is representative."],
            "unknowns": ["Unsampled frames."],
            "confidence_score": 0.74,
            "evidence": ["frame_0000.png"],
            "risks": ["Motion could fail between samples."],
            "counterarguments": ["The pose is readable."],
            "recommendation": "Continue review.",
            "tradeoffs": ["More samples cost runtime."],
            "what_would_change_recommendation": ["A later frame with a blocker."],
        }
    }
    provider = FakeProvider(response_signals=signals)
    verdict = verify(manifest=sample_manifest, frames_dir=frames_dir, providers=[provider])
    assert verdict.frame_analyses[0].response_quality is not None
    assert verdict.frame_analyses[0].response_quality.confidence_score == 0.74


# ---------------------------------------------------------------------------
# Value coercion helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        ("true", True),
        ("YES", True),
        ("1", True),
        ("  true  ", True),
        ("false", False),
        ("no", False),
        ("0", False),
        ("maybe", None),
        (42, None),
        (None, None),
    ],
)
def test_as_bool(value: Any, expected: bool | None) -> None:
    assert _as_bool(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (3, 3.0),
        (3.5, 3.5),
        ("4", 4.0),
        ("  2.5 ", 2.5),
        (True, None),  # bool is an int subclass but must not coerce to 1.0
        (False, None),
        ("not-a-number", None),
        (None, None),
        ([1, 2], None),
    ],
)
def test_as_number(value: Any, expected: float | None) -> None:
    assert _as_number(value) == expected


# ---------------------------------------------------------------------------
# Per-signal hard-fail branches (evaluate_frame_signals)
# ---------------------------------------------------------------------------


def _manifest_all_flags() -> Manifest:
    """A manifest that activates every character + landmark gated signal."""
    return Manifest(
        shot_id="x",
        expected_characters=[ExpectedCharacter(id="hero")],
        expected_landmarks=["village"],
        quality_thresholds=QualityThresholds(),
    )


def test_evaluate_clean_result_has_no_failures(passing_signals: dict[str, Any]) -> None:
    result = ProviderResult("gemma", "gemma4:latest", dict(passing_signals))
    assert evaluate_frame_signals("frame_0000.png", result, _manifest_all_flags()) == []


@pytest.mark.parametrize(
    ("override", "expected_signal"),
    [
        ({"character_visible": False}, "character_visible"),
        ({"landmark_visible": False}, "landmark_visible"),
        ({"character_pose_plausible": False}, "character_pose_plausible"),
        ({"ground_contact_visible": False}, "ground_contact_visible"),
        ({"scale_plausible": False}, "scale_plausible"),
        (
            {"character_orientation_matches_movement": False},
            "character_orientation_matches_movement",
        ),
        ({"wardrobe_present": False}, "wardrobe_present"),
        ({"head_covering_or_hair_present": False}, "head_covering_or_hair_present"),
        (
            {"character_identity_matches_manifest": False},
            "character_identity_matches_manifest",
        ),
        ({"severity": "blocking"}, "severity"),
        ({"debug_quality_or_broken": True}, "debug_quality_or_broken"),
        ({"character_orientation": "ragdoll"}, "character_orientation"),
        ({"lighting_quality": 1}, "lighting_quality"),
    ],
)
def test_each_signal_branch_triggers(
    passing_signals: dict[str, Any],
    override: dict[str, Any],
    expected_signal: str,
) -> None:
    signals = passing_signals | override
    result = ProviderResult("gemma", "gemma4:latest", signals)
    failures = evaluate_frame_signals("frame_0000.png", result, _manifest_all_flags())
    assert expected_signal in {f.signal for f in failures}


def test_provider_error_result_yields_single_marker_failure(
    sample_manifest: Manifest,
) -> None:
    """An infra failure becomes exactly one ``__provider_error__`` finding."""
    result = ProviderResult(
        "nvidia-primary", "m", {}, error="nvidia: connection refused"
    )
    failures = evaluate_frame_signals("frame_0000.png", result, sample_manifest)
    assert len(failures) == 1
    assert failures[0].signal == "__provider_error__"
    assert failures[0].value == "nvidia: connection refused"


def test_character_flags_off_skip_gated_signals(passing_signals: dict[str, Any]) -> None:
    """When the character's must_* flags are off, those signals can't fail even
    if the provider reports the bad value."""
    manifest = Manifest(
        shot_id="x",
        expected_characters=[
            ExpectedCharacter(
                id="hero",
                must_be_visible=False,
                must_be_upright=False,
                must_have_ground_contact=False,
                must_have_wardrobe=False,
                must_have_hair_or_head_covering=False,
                must_match_identity=False,
            )
        ],
    )
    bad = passing_signals | {
        "character_visible": False,
        "character_orientation": "lying_horizontal",
        "ground_contact_visible": False,
        "wardrobe_present": False,
        "head_covering_or_hair_present": False,
        "character_identity_matches_manifest": False,
    }
    result = ProviderResult("gemma", "gemma4:latest", bad)
    failures = evaluate_frame_signals("frame_0000.png", result, manifest)
    gated = {
        "character_visible",
        "character_orientation",
        "ground_contact_visible",
        "wardrobe_present",
        "head_covering_or_hair_present",
        "character_identity_matches_manifest",
    }
    assert gated.isdisjoint({f.signal for f in failures})
