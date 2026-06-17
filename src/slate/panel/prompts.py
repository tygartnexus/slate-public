"""Shared prompt scaffolding for Panel personas.

Every persona's prompt follows the same template:

1. **Identity** — who the persona is and their professional viewpoint.
2. **Adversarial framing** — explicitly tasked to find reasons NOT to publish.
3. **Criteria** — what this persona evaluates (persona-specific).
4. **Frame labels** — names of the frames being reviewed.
5. **Output schema** — strict JSON the persona must return.
6. **Context** — the manifest description and Core verdict summary.

Centralizing the scaffold lets individual persona modules focus on their
unique identity + criteria, while keeping the JSON contract uniform so
:mod:`slate.panel.fusion` can parse every persona the same way.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from slate.manifest import Manifest
from slate.response_quality import ResponseMode, build_response_quality_prompt
from slate.verdict import Verdict

#: Strict-JSON schema every persona MUST follow.
PERSONA_OUTPUT_SCHEMA = textwrap.dedent(
    """\
    Return STRICT JSON (no markdown fences, no preamble) with this shape:

    {
      "publish_ready": true | false,
      "summary": "one sentence covering your overall judgment",
      "flags": [
        {
          "category": "<one of the categories you evaluate>",
          "severity": "critical" | "high" | "medium" | "low",
          "frame": "<frame filename or null if shot-wide>",
          "description": "<concrete, specific observation; no hedging>"
        }
      ],
      "per_frame_notes": {
        "<frame filename>": "<one line — what stood out for THIS frame>"
      }
    }

    Severity guide:
      critical = publish-blocking; the shot cannot ship like this
      high     = strong reason to not publish; needs another take
      medium   = noticeable issue; tolerable in low-stakes contexts
      low      = nit; mention for polish but does not block

    If you find no issues, return an empty flags list and publish_ready=true.
    If you find ANY critical or 2+ high flags, return publish_ready=false.

    The same JSON object must also include `response_quality` using the shared
    Slate response-quality contract.
    """
)

PERSONA_RESPONSE_QUALITY_CONTRACT = build_response_quality_prompt(
    mode=ResponseMode.RED_TEAM,
    subject="this persona's publish-readiness review",
)


def build_persona_prompt(
    *,
    identity: str,
    criteria: list[str],
    frame_paths: list[Path],
    manifest: Manifest,
    core_verdict: Verdict,
) -> str:
    """Compose the full prompt for one persona."""
    frame_names = "\n".join(f"  - {p.name}" for p in frame_paths)
    criteria_block = "\n".join(f"  - {c}" for c in criteria)
    core_summary = _summarize_core_verdict(core_verdict)
    shot_desc = manifest.description or "(no description provided)"
    primary_char = manifest.primary_character()
    char_desc = primary_char.description if primary_char else "the character in the scene"
    landmarks = manifest.landmarks_text()

    return textwrap.dedent(
        f"""\
        {identity}

        You are part of a four-persona red team evaluating a rendered animation
        shot. Your job is to find reasons this shot should NOT ship. Be specific,
        be concrete, anchor every observation to a frame when possible. Do not
        hedge. If the work is solid, say so plainly — but bias toward finding
        issues, not toward approval.

        ## Shot context

        Shot description: {shot_desc}
        Expected character: {char_desc}
        Expected landmarks / setting: {landmarks}

        ## Core VLM verdict (for context only — do not just rubber-stamp it)

        {core_summary}

        ## Frames you are reviewing

        {frame_names}

        ## What you evaluate

        {criteria_block}

        ## Output

        {PERSONA_OUTPUT_SCHEMA}

        {PERSONA_RESPONSE_QUALITY_CONTRACT}
        """
    ).strip()


def _summarize_core_verdict(verdict: Verdict) -> str:
    if not verdict.failures:
        return f"Core status: {verdict.status.value}; no signal failures."
    sample = verdict.failures[:5]
    lines = [f"Core status: {verdict.status.value}; {len(verdict.failures)} failure(s):"]
    for f in sample:
        lines.append(f"  - [{f.signal}] {f.frame}: {f.value}")
    if len(verdict.failures) > 5:
        lines.append(f"  ... and {len(verdict.failures) - 5} more")
    return "\n".join(lines)
