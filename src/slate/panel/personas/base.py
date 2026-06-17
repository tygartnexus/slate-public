"""Persona protocol + shared run helper.

Every Panel persona is a small class implementing :meth:`evaluate`. The
shared :func:`run_persona` helper handles the boilerplate of calling the
Claude client, parsing JSON, and packaging the result into a
:class:`PersonaVerdict` — so individual personas only declare their identity
and criteria.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol

from slate.manifest import Manifest
from slate.panel.claude_client import ClaudeResponse
from slate.panel.prompts import build_persona_prompt
from slate.panel.verdict import PersonaFlag, PersonaVerdict, Severity
from slate.response_quality import (
    missing_evidence_report,
    parse_response_quality_report,
)
from slate.verdict import Verdict


class Persona(Protocol):
    """A Panel persona — one professional viewpoint that critiques the shot."""

    name: str
    weight: float

    def evaluate(
        self,
        *,
        frames: list[Path],
        manifest: Manifest,
        core_verdict: Verdict,
        client: VisionPanelClient,
    ) -> PersonaVerdict: ...


class VisionPanelClient(Protocol):
    """Small interface shared by Claude and local Ollama panel clients."""

    model: str

    def analyze(self, prompt: str, frames: list[Path]) -> ClaudeResponse: ...


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```\s*$", re.MULTILINE)


def run_persona(
    *,
    name: str,
    identity: str,
    criteria: list[str],
    frames: list[Path],
    manifest: Manifest,
    core_verdict: Verdict,
    client: VisionPanelClient,
) -> PersonaVerdict:
    """Run one persona end-to-end and return its verdict."""
    prompt = build_persona_prompt(
        identity=identity,
        criteria=criteria,
        frame_paths=frames,
        manifest=manifest,
        core_verdict=core_verdict,
    )

    response = client.analyze(prompt, frames)

    if not response.ok:
        return PersonaVerdict(
            name=name,
            model=client.model,
            publish_ready=False,
            summary="(provider error — see error field)",
            response_quality=missing_evidence_report(
                facts=[f"{name} persona provider failed."],
                recommendation="Do not rely on this persona review; rerun after fixing provider access.",
                confidence_score=0.2,
                unknown="The persona did not produce evidence because the provider call failed.",
                risk="An incomplete panel can make publish readiness look stronger than the evidence supports.",
            ),
            error=response.error,
            raw_response=response.text,
        )

    parsed = _parse_persona_json(response.text)
    if parsed is None:
        return PersonaVerdict(
            name=name,
            model=client.model,
            publish_ready=False,
            summary="(persona returned malformed JSON)",
            response_quality=missing_evidence_report(
                facts=[f"{name} persona returned malformed JSON."],
                recommendation="Do not rely on this persona review; rerun until structured JSON is returned.",
                confidence_score=0.2,
                unknown="The persona's facts, assumptions, confidence, evidence, and risks are missing.",
                risk="Malformed JSON can hide unsupported or contradictory persona reasoning.",
            ),
            error=f"could not parse persona JSON: {response.text[:200]}",
            raw_response=response.text,
        )

    response_quality = parse_response_quality_report(parsed)
    if response_quality is None:
        has_response_quality = isinstance(parsed.get("response_quality"), dict)
        issue = "invalid" if has_response_quality else "missing"
        return PersonaVerdict(
            name=name,
            model=client.model,
            publish_ready=False,
            summary=f"(persona returned {issue} response_quality)",
            response_quality=missing_evidence_report(
                facts=[f"{name} persona returned JSON with {issue} response_quality."],
                recommendation="Reject this persona output and rerun with the response-quality contract enforced.",
                confidence_score=0.25,
                unknown="Required facts, assumptions, unknowns, confidence, evidence, risks, counterarguments, tradeoffs, and change criteria were not provided.",
                risk="Accepting persona output without the quality contract can make unsupported claims sound verified.",
            ),
            error=f"persona JSON has {issue} response_quality object",
            raw_response=response.text,
        )

    flags = [
        PersonaFlag(
            category=str(f.get("category", "uncategorized")),
            severity=_clamp_severity(f.get("severity")),
            frame=f.get("frame") if isinstance(f.get("frame"), str) else None,
            description=str(f.get("description", "")),
        )
        for f in parsed.get("flags", [])
        if isinstance(f, dict)
    ]

    per_frame_raw = parsed.get("per_frame_notes", {})
    per_frame: dict[str, str] = {}
    if isinstance(per_frame_raw, dict):
        for k, v in per_frame_raw.items():
            if isinstance(k, str) and isinstance(v, str):
                per_frame[k] = v

    publish_ready = bool(parsed.get("publish_ready", False))

    return PersonaVerdict(
        name=name,
        model=client.model,
        publish_ready=publish_ready,
        summary=str(parsed.get("summary", "")),
        flags=flags,
        per_frame_notes=per_frame,
        response_quality=response_quality,
        raw_response=response.text,
    )


def _parse_persona_json(text: str) -> dict[str, Any] | None:
    cleaned = _FENCE_RE.sub("", text).strip()
    if not cleaned.startswith("{") and "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.find("{") : cleaned.rfind("}") + 1]
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _clamp_severity(value: object) -> Severity:
    raw = str(value).strip().lower() if value is not None else "medium"
    if raw == "critical":
        return "critical"
    if raw == "high":
        return "high"
    if raw == "low":
        return "low"
    return "medium"
