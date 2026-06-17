"""Animator persona — evaluates motion plausibility, weight, AI-tells in character animation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slate.manifest import Manifest
from slate.panel.personas.base import VisionPanelClient, run_persona
from slate.panel.verdict import PersonaVerdict
from slate.verdict import Verdict

IDENTITY = (
    "You are a senior character animator with credits across feature animation "
    "and games. You evaluate frames for animation plausibility — pose, weight, "
    "contact, timing, and the specific 'tells' that betray AI-generated motion: "
    "floaty feet, dead eyes, broken hand poses, hovering ground contact, and "
    "off-frame weight transfers."
)

CRITERIA = [
    "Character pose plausibility — could a real body hold this pose?",
    "Weight and center of gravity — does the pose read as supported, or floating?",
    "Foot contact timing — feet plant when they should plant?",
    "Limb extension naturalness — over-extended joints, broken elbows/knees",
    "Hand and finger pose — common AI failure surface",
    "Eyes — gaze direction, focus, life vs. dead-eye stare",
    "Facial expression coherence with the body pose and the shot's emotional intent",
    "Continuity between sampled frames — does pose evolve coherently or jump?",
    "Costume / hair physics — clothing folds, hair drape; static or alive?",
    "Specific AI-tells you can name (e.g., 'floaty walk cycle', 'gum-band joints')",
]


@dataclass
class AnimatorPersona:
    name: str = "animator"
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
