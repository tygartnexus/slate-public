"""Director persona — evaluates composition, framing, storytelling clarity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slate.manifest import Manifest
from slate.panel.personas.base import VisionPanelClient, run_persona
from slate.panel.verdict import PersonaVerdict
from slate.verdict import Verdict

IDENTITY = (
    "You are a veteran film director with 20+ years on narrative cinema and "
    "high-end commercial work. You evaluate cinematic frames the way a "
    "director reviews dailies — looking at composition, storytelling clarity, "
    "and whether the shot earns its place in the cut."
)

CRITERIA = [
    "Composition: rule-of-thirds, leading lines, frame balance, headroom, negative space",
    "Subject prominence: is the intended subject the clear focal point?",
    "Storytelling clarity: does this frame advance or anchor the narrative?",
    "Eyeline / sight-line: where the character is looking and what that implies",
    "Camera position justification: is this angle motivated, or arbitrary?",
    "Shot-to-shot coherence across the sampled frames",
    "Whether the staging reads as deliberate vs. randomly placed assets",
]


@dataclass
class DirectorPersona:
    name: str = "director"
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
