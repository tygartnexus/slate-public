"""Shared pytest fixtures.

Provides:
* :func:`fake_provider` — drop-in :class:`slate.providers.base.VLMProvider`
  whose response can be programmed per test.
* :func:`sample_manifest` — a populated :class:`slate.manifest.Manifest`.
* :func:`frames_dir` — a tmp directory containing a small sequence of solid-color
  PNGs so frame-listing / sampling code has real bytes to chew on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from slate.manifest import (
    ExpectedCharacter,
    FrameSampling,
    Manifest,
    QualityThresholds,
)
from slate.panel.claude_client import ClaudeResponse
from slate.providers.base import ProviderResult
from slate.verdict import Verdict, VerdictStatus

# ---------------------------------------------------------------------------
# Fake Panel client
# ---------------------------------------------------------------------------


@dataclass
class FakeClaudeClient:
    """A drop-in for Panel vision clients. Programmable response per test."""

    model: str = "claude-sonnet-4-6"
    response_text: str = ""
    error: str | None = None
    calls: list[tuple[str, list[Path]]] = field(default_factory=list)

    def analyze(self, prompt: str, frames: list[Path]) -> ClaudeResponse:
        self.calls.append((prompt, list(frames)))
        return ClaudeResponse(text=self.response_text, model=self.model, error=self.error)


def passing_persona_json(persona_name: str) -> str:
    """A persona response that should publish with no flags."""
    return json.dumps(
        {
            "publish_ready": True,
            "summary": f"{persona_name} approves",
            "flags": [],
            "per_frame_notes": {},
            "response_quality": _response_quality(
                recommendation="Treat this persona as passing, subject to the other personas."
            ),
        }
    )


def critical_persona_json(persona_name: str, frame: str = "frame_0000.png") -> str:
    """A persona response that raises one critical flag."""
    return json.dumps(
        {
            "publish_ready": False,
            "summary": f"{persona_name} blocks publish",
            "flags": [
                {
                    "category": "test_critical",
                    "severity": "critical",
                    "frame": frame,
                    "description": f"blocking issue found by {persona_name}",
                }
            ],
            "per_frame_notes": {},
            "response_quality": _response_quality(
                recommendation="Block publish until this critical issue is fixed."
            ),
        }
    )


def _response_quality(*, recommendation: str) -> dict[str, object]:
    return {
        "facts": ["Persona reviewed sampled frames."],
        "assumptions": ["The manifest context is accurate."],
        "unknowns": ["Unsampled frames were not reviewed."],
        "confidence_score": 0.78,
        "evidence": ["sampled frame review"],
        "risks": ["The issue could vary between frames."],
        "counterarguments": ["Other personas may disagree."],
        "recommendation": recommendation,
        "tradeoffs": ["More review improves confidence but costs time."],
        "what_would_change_recommendation": ["Additional frames contradict this finding."],
    }

# ---------------------------------------------------------------------------
# Sample manifest
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_manifest() -> Manifest:
    return Manifest(
        shot_id="village_walk_001",
        description="medieval villager walks past a cobblestone bridge",
        expected_characters=[
            ExpectedCharacter(id="hero", description="medieval female peasant")
        ],
        expected_landmarks=["village", "cobblestone path"],
        quality_thresholds=QualityThresholds(
            lighting=3, composition=3, atmosphere=3, mood_readability=3, visual_coherence=3
        ),
        frame_sampling=FrameSampling(mode="first_mid_last"),
    )


# ---------------------------------------------------------------------------
# Fake provider
# ---------------------------------------------------------------------------


@dataclass
class FakeProvider:
    """A provider that replays a canned response. Used to test the engine
    without hitting Ollama or NVIDIA."""

    label: str = "fake"
    model: str = "fake:1"
    response_signals: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    calls: list[Path] = field(default_factory=list)

    def analyze_frame(self, frame_path: Path, manifest) -> ProviderResult:  # type: ignore[no-untyped-def]
        self.calls.append(frame_path)
        return ProviderResult(
            provider=self.label,
            model=self.model,
            signals=dict(self.response_signals),
            error=self.error,
        )


@pytest.fixture
def passing_signals() -> dict[str, Any]:
    """A provider response that should produce VerdictStatus.PASS."""
    return {
        "character_visible": True,
        "character_orientation": "upright_walking",
        "character_pose_plausible": True,
        "character_orientation_matches_movement": True,
        "ground_contact_visible": True,
        "scale_plausible": True,
        "landmark_visible": True,
        "debug_quality_or_broken": False,
        "wardrobe_present": True,
        "head_covering_or_hair_present": True,
        "character_identity_matches_manifest": True,
        "lighting_quality": 4,
        "composition_quality": 4,
        "atmosphere_quality": 4,
        "mood_readability": 4,
        "visual_coherence": 4,
        "severity": "ok",
        "description": "upright walker, ground contact present, good composition",
        "response_quality": {
            "facts": ["The sampled frame shows the expected character upright."],
            "assumptions": ["The sampled frames represent the shot."],
            "unknowns": ["Unsampled frames were not inspected."],
            "confidence_score": 0.74,
            "evidence": ["sampled frame pixels", "shot manifest"],
            "risks": ["Motion failures can occur between sampled frames."],
            "counterarguments": ["Additional providers could disagree."],
            "recommendation": "Treat this provider result as passing automated checks.",
            "tradeoffs": ["More sampling improves coverage but costs more runtime."],
            "what_would_change_recommendation": [
                "A sampled frame with a hard-fail signal.",
                "Provider disagreement on the same frame.",
            ],
        },
    }


@pytest.fixture
def passing_core_verdict() -> Verdict:
    return Verdict(
        status=VerdictStatus.PASS,
        shot_id="village_walk_001",
        slate_version="0.1.0",
        started_at="2026-05-20T00:00:00Z",
        finished_at="2026-05-20T00:00:05Z",
        duration_seconds=5.0,
        providers_consulted=["gemma"],
        frames_analyzed=["frame_0000.png", "frame_0005.png", "frame_0009.png"],
        failures=[],
        frame_analyses=[],
        quality_scores_aggregated={"lighting_quality": 4.0},
    )


@pytest.fixture
def failing_core_verdict(passing_core_verdict: Verdict) -> Verdict:
    return passing_core_verdict.model_copy(update={"status": VerdictStatus.FAIL})


@pytest.fixture
def indeterminate_core_verdict(passing_core_verdict: Verdict) -> Verdict:
    return passing_core_verdict.model_copy(update={"status": VerdictStatus.INDETERMINATE})


# ---------------------------------------------------------------------------
# Frames directory
# ---------------------------------------------------------------------------


def _make_png(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (8, 8), color).save(path, "PNG")


@pytest.fixture
def frames_dir(tmp_path: Path) -> Path:
    """tmp dir with frame_0000..frame_0009.png (alternating solid colors)."""
    d = tmp_path / "frames"
    d.mkdir()
    for i in range(10):
        color = (255, 255, 255) if i % 2 == 0 else (0, 0, 0)
        _make_png(d / f"frame_{i:04d}.png", color)
    return d


@pytest.fixture
def black_frames_dir(tmp_path: Path) -> Path:
    """tmp dir with 3 all-black frames — the canonical 'broken render' fixture."""
    d = tmp_path / "frames_black"
    d.mkdir()
    for i in range(3):
        _make_png(d / f"frame_{i:04d}.png", (0, 0, 0))
    return d
