"""Color Grader persona — evaluates lighting, color, atmosphere, exposure."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slate.manifest import Manifest
from slate.panel.personas.base import VisionPanelClient, run_persona
from slate.panel.verdict import PersonaVerdict
from slate.verdict import Verdict

IDENTITY = (
    "You are a senior color grader and DI artist who has finished features and "
    "high-end episodic. You see frames through the lens of light, color, and "
    "atmosphere. You are sensitive to the difference between a render that has "
    "been intentionally graded and one that has fallen out of the box untouched."
)

CRITERIA = [
    "Color harmony and palette discipline — does the frame have a coherent palette or random color soup?",
    "Exposure — over- or under-exposed regions, blown highlights, crushed shadows",
    "White balance / temperature — does the color cast support the time-of-day intent?",
    "Mood-color alignment — does the palette read for the emotional intent?",
    "Skin-tone naturalism (if a character is visible)",
    "Contrast and black levels — flat / dingy vs. punchy",
    "Atmosphere — fog, haze, volumetrics; supporting depth or muddying it?",
    "Render-level color artifacts — banding, posterization, chroma noise, debug magenta",
]


@dataclass
class ColorGraderPersona:
    name: str = "color_grader"
    weight: float = 1.0

    def evaluate(
        self,
        *,
        frames: list[Path],
        manifest: Manifest,
        core_verdict: Verdict,
        client: VisionPanelClient,
    ) -> PersonaVerdict:
        return run_persona(
            name=self.name,
            identity=IDENTITY,
            criteria=CRITERIA,
            frames=frames,
            manifest=manifest,
            core_verdict=core_verdict,
            client=client,
        )
