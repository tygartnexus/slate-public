"""Slate manifest schema.

A Slate manifest describes *what should be in a rendered shot* in tool-agnostic
terms — no UE5 or Blender concepts leak in. The manifest drives both the prompt
sent to each VLM provider and the rules used to convert provider answers into
PASS/FAIL.

Schema is versioned by Pydantic model; the on-disk JSON ``slate_version`` field
mirrors the package version that wrote it but is informational only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExpectedCharacter(BaseModel):
    """One character the manifest expects to see in the shot."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str = "humanoid character in the scene"
    must_be_visible: bool = True
    must_be_upright: bool = True
    must_have_ground_contact: bool = True
    must_have_wardrobe: bool = True
    must_have_hair_or_head_covering: bool = True
    must_match_identity: bool = True


class QualityThresholds(BaseModel):
    """Minimum acceptable scores (1-5) per quality axis.

    A score below the threshold for any configured axis produces a failure.
    Set an axis to ``None`` to skip it.
    """

    model_config = ConfigDict(extra="forbid")

    lighting: int | None = 3
    composition: int | None = 3
    atmosphere: int | None = 3
    mood_readability: int | None = 3
    visual_coherence: int | None = 3

    def thresholds(self) -> dict[str, int]:
        """Like :meth:`as_dict` but with ``None`` axes removed."""
        raw = {
            "lighting_quality": self.lighting,
            "composition_quality": self.composition,
            "atmosphere_quality": self.atmosphere,
            "mood_readability": self.mood_readability,
            "visual_coherence": self.visual_coherence,
        }
        return {k: v for k, v in raw.items() if v is not None}


class FrameSampling(BaseModel):
    """Which frames in the sequence to send to the VLMs.

    `first_mid_last` (default) sends 3 frames per shot — cheap and cheerful.
    `every_n` walks the sequence at a stride.
    `explicit` sends a hand-picked list of frame indices (0-based).
    """

    model_config = ConfigDict(extra="forbid")

    mode: Literal["first_mid_last", "every_n", "explicit"] = "first_mid_last"
    every_n: int = 60
    explicit_indices: list[int] = Field(default_factory=list)


class Manifest(BaseModel):
    """The top-level Slate manifest.

    Minimal valid manifest:

    .. code-block:: json

        {"shot_id": "village_walk_001"}

    A more typical manifest:

    .. code-block:: json

        {
          "shot_id": "village_walk_001",
          "expected_characters": [
            {"id": "hero", "description": "medieval female peasant"}
          ],
          "expected_landmarks": ["village", "cobblestone path"],
          "quality_thresholds": {"lighting": 4, "composition": 4}
        }
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    shot_id: str
    description: str = ""
    expected_characters: list[ExpectedCharacter] = Field(default_factory=list)
    expected_landmarks: list[str] = Field(default_factory=list)
    quality_thresholds: QualityThresholds = Field(default_factory=QualityThresholds)
    frame_sampling: FrameSampling = Field(default_factory=FrameSampling)
    frame_dir: str | None = None
    frame_count_expected: int | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> Manifest:
        """Load and validate a manifest from a JSON file."""
        data = json.loads(Path(path).read_text("utf-8"))
        return cls.model_validate(data)

    def primary_character(self) -> ExpectedCharacter | None:
        """Convenience: the first expected character, if any."""
        return self.expected_characters[0] if self.expected_characters else None

    def landmarks_text(self) -> str:
        """Comma-joined landmark list for prompt embedding."""
        return ", ".join(self.expected_landmarks) if self.expected_landmarks else "scene environment"
