"""Persona tests using the fake Claude client.

These tests verify that personas:
1. Construct a non-empty prompt and send the right frames.
2. Parse a passing JSON response into a publish_ready PersonaVerdict.
3. Parse a critical JSON response into a blocking PersonaVerdict.
4. Surface provider errors as PersonaVerdict.error.
5. Handle malformed JSON gracefully.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from slate.frames import list_frames
from slate.manifest import Manifest
from slate.panel.personas import (
    AnimatorPersona,
    AudiencePersona,
    ColorGraderPersona,
    DirectorPersona,
)
from slate.verdict import Verdict
from tests.conftest import (
    FakeClaudeClient,
    critical_persona_json,
    passing_persona_json,
)

PERSONA_CLASSES = [
    DirectorPersona,
    ColorGraderPersona,
    AnimatorPersona,
    AudiencePersona,
]


@pytest.mark.parametrize("persona_cls", PERSONA_CLASSES)
def test_persona_returns_publish_ready_for_passing_json(
    persona_cls,
    sample_manifest: Manifest,
    passing_core_verdict: Verdict,
    frames_dir: Path,
) -> None:
    persona = persona_cls()
    client = FakeClaudeClient(response_text=passing_persona_json(persona.name))
    frames = list_frames(frames_dir)
    result = persona.evaluate(
        frames=frames,
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert result.ok
    assert result.publish_ready is True
    assert result.flags == []
    assert result.name == persona.name
    assert result.response_quality is not None
    assert result.response_quality.confidence_score > 0
    assert result.response_quality.tradeoffs
    # Sanity check: the persona constructed a non-empty prompt and sent the
    # frames to the client.
    assert client.calls, "client.analyze was never called"
    sent_prompt, sent_frames = client.calls[0]
    assert sent_prompt
    assert sent_frames == frames


@pytest.mark.parametrize("persona_cls", PERSONA_CLASSES)
def test_persona_raises_critical_for_blocking_json(
    persona_cls,
    sample_manifest: Manifest,
    passing_core_verdict: Verdict,
    frames_dir: Path,
) -> None:
    persona = persona_cls()
    client = FakeClaudeClient(
        response_text=critical_persona_json(persona.name, "frame_0000.png")
    )
    frames = list_frames(frames_dir)
    result = persona.evaluate(
        frames=frames,
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert result.ok
    assert result.publish_ready is False
    assert any(f.severity == "critical" for f in result.flags)


def test_persona_surfaces_provider_error(
    sample_manifest: Manifest,
    passing_core_verdict: Verdict,
    frames_dir: Path,
) -> None:
    client = FakeClaudeClient(error="anthropic: 401 unauthorized")
    frames = list_frames(frames_dir)
    result = DirectorPersona().evaluate(
        frames=frames,
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert not result.ok
    assert "anthropic" in (result.error or "")
    assert result.publish_ready is False


def test_persona_handles_garbage_response(
    sample_manifest: Manifest,
    passing_core_verdict: Verdict,
    frames_dir: Path,
) -> None:
    client = FakeClaudeClient(response_text="this isn't JSON, just prose")
    frames = list_frames(frames_dir)
    result = DirectorPersona().evaluate(
        frames=frames,
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert not result.ok
    assert "could not parse" in (result.error or "")


def test_persona_handles_markdown_fenced_json(
    sample_manifest: Manifest,
    passing_core_verdict: Verdict,
    frames_dir: Path,
) -> None:
    """Some models wrap JSON in ```json``` fences even when asked not to."""
    client = FakeClaudeClient(
        response_text="```json\n" + passing_persona_json("director") + "\n```"
    )
    frames = list_frames(frames_dir)
    result = DirectorPersona().evaluate(
        frames=frames,
        manifest=sample_manifest,
        core_verdict=passing_core_verdict,
        client=client,
    )
    assert result.ok
    assert result.publish_ready is True
