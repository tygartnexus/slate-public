"""Manifest schema tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from slate.manifest import (
    ExpectedCharacter,
    FrameSampling,
    Manifest,
    QualityThresholds,
)


def test_minimal_manifest_is_valid() -> None:
    m = Manifest(shot_id="x")
    assert m.shot_id == "x"
    assert m.expected_characters == []
    assert m.expected_landmarks == []
    assert m.quality_thresholds.lighting == 3


def test_unknown_top_level_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate({"shot_id": "x", "totally_made_up": 42})


def test_unknown_character_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(
            {
                "shot_id": "x",
                "expected_characters": [{"id": "hero", "bogus": True}],
            }
        )


def test_quality_thresholds_drops_none_axes() -> None:
    q = QualityThresholds(lighting=4, composition=None, atmosphere=3)
    out = q.thresholds()
    assert out == {
        "lighting_quality": 4,
        "atmosphere_quality": 3,
        "mood_readability": 3,
        "visual_coherence": 3,
    }


def test_primary_character() -> None:
    m = Manifest(
        shot_id="x",
        expected_characters=[
            ExpectedCharacter(id="hero"),
            ExpectedCharacter(id="extra"),
        ],
    )
    assert m.primary_character() is not None
    assert m.primary_character().id == "hero"  # type: ignore[union-attr]


def test_landmarks_text_default() -> None:
    assert Manifest(shot_id="x").landmarks_text() == "scene environment"


def test_landmarks_text_joined() -> None:
    m = Manifest(shot_id="x", expected_landmarks=["village", "bridge"])
    assert m.landmarks_text() == "village, bridge"


def test_from_file_roundtrip(tmp_path: Path) -> None:
    payload = {
        "shot_id": "x",
        "expected_characters": [{"id": "hero"}],
        "frame_sampling": {"mode": "every_n", "every_n": 30},
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(payload), "utf-8")
    m = Manifest.from_file(p)
    assert m.shot_id == "x"
    assert m.frame_sampling.mode == "every_n"
    assert m.frame_sampling.every_n == 30


def test_frame_sampling_explicit_indices() -> None:
    s = FrameSampling(mode="explicit", explicit_indices=[0, 50, 100])
    assert s.explicit_indices == [0, 50, 100]
