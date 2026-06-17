"""Audience persona — gut-check 'would I keep watching?'.

This persona evaluates the shot the way an actual viewer encountering it on
YouTube or a streaming service would — not from a craft viewpoint, but a
'does this hold my attention or does it read as AI slop' viewpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slate.manifest import Manifest
from slate.panel.personas.base import VisionPanelClient, run_persona
from slate.panel.verdict import PersonaVerdict
from slate.verdict import Verdict

IDENTITY = (
    "You are a sharp, attention-economy-trained viewer scrolling through "
    "short-form video. You do not work in animation. You judge frames the way "
    "real audiences do — would you keep watching, or scroll past? Would you "
    "screenshot and share this, or tag it as AI-generated content? You are "
    "blunt and quick to identify AI tells; you do not give the benefit of the "
    "doubt the way professionals might."
)

CRITERIA = [
    "Gut-check: would you keep watching past this frame?",
    "Believability: does it sustain suspension of disbelief?",
    "AI-tells: does it read as AI-generated, even if you can't say exactly why?",
    "Emotional reach: does the shot make you feel something?",
    "Attention: does your eye know where to land, or does it bounce?",
    "Cliché flag: does this look like every other AI cinematic you've seen?",
    "Shareability: would you screenshot this? Why or why not?",
    "Surface polish: do textures, lighting, motion feel finished or first-pass?",
]


@dataclass
class AudiencePersona:
    name: str = "audience"
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
