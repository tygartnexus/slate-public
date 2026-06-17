"""Panel ensemble — orchestrates personas and produces an EnhancedVerdict.

The ensemble:

1. Takes a Core :class:`slate.verdict.Verdict` (already produced) plus the
   manifest and the sampled frames.
2. Skips itself entirely if the Core verdict is FAIL or INDETERMINATE — no
   sense burning Claude tokens on a render that's already blocked.
3. Runs every configured persona, sequentially (parallelism is a v2 nicety).
4. Fuses the per-persona results via :func:`slate.panel.fusion.fuse`.
5. Wraps Core + Panel into a single :class:`EnhancedVerdict`.
"""

from __future__ import annotations

import time
from pathlib import Path

from slate import __version__
from slate.frames import list_frames, sample_frames
from slate.manifest import Manifest
from slate.panel.claude_client import ClaudeVisionClient
from slate.panel.fusion import fuse
from slate.panel.personas import Persona, default_panel_personas
from slate.panel.personas.base import VisionPanelClient
from slate.panel.verdict import EnhancedVerdict
from slate.verdict import Verdict, VerdictStatus


def run_panel(
    *,
    core_verdict: Verdict,
    manifest: Manifest,
    frames_dir: Path,
    client: VisionPanelClient | None = None,
    personas: list[Persona] | None = None,
) -> EnhancedVerdict:
    """Run the Panel ensemble against a Core verdict, return an EnhancedVerdict.

    If ``core_verdict.status`` is FAIL or INDETERMINATE, Panel is skipped
    (no Claude calls) and the returned EnhancedVerdict carries
    ``panel=None`` with the appropriate final status.
    """
    if core_verdict.status in (VerdictStatus.FAIL, VerdictStatus.INDETERMINATE):
        return EnhancedVerdict.from_core_and_panel(core_verdict, None)

    if personas is None:
        personas = default_panel_personas()
    if client is None:
        client = ClaudeVisionClient()

    all_frames = list_frames(frames_dir)
    sampled = sample_frames(all_frames, manifest.frame_sampling)

    started = time.monotonic()
    per_persona = [
        persona.evaluate(
            frames=sampled,
            manifest=manifest,
            core_verdict=core_verdict,
            client=client,
        )
        for persona in personas
    ]
    duration = round(time.monotonic() - started, 3)

    panel = fuse(per_persona, slate_version=__version__, duration_seconds=duration)
    return EnhancedVerdict.from_core_and_panel(core_verdict, panel)


__all__ = ["run_panel"]
