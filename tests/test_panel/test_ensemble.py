"""End-to-end ensemble tests.

These tests verify that ``run_panel`` orchestrates all 4 personas and produces
a coherent EnhancedVerdict. Like the persona tests, no real Claude calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from slate.manifest import Manifest
from slate.panel.ensemble import run_panel
from slate.panel.verdict import EnhancedStatus
from slate.verdict import Verdict
from tests.conftest import FakeClaudeClient, passing_persona_json


def test_run_panel_skipped_when_core_failed(
    sample_manifest: Manifest,
    failing_core_verdict: Verdict,
    frames_dir: Path,
) -> None:
    """Panel should not burn Claude tokens on a render Core already failed."""
    client = FakeClaudeClient(response_text=passing_persona_json("director"))
    enhanced = run_panel(
        core_verdict=failing_core_verdict,
        manifest=sample_manifest,
        frames_dir=frames_dir,
        client=client,
    )
    assert enhanced.final_status == EnhancedStatus.FAIL
    assert enhanced.panel is None
    assert client.calls == []  # no calls made


def test_run_panel_skipped_when_core_indeterminate(
    sample_manifest: Manifest,
    indeterminate_core_verdict: Verdict,
    frames_dir: Path,
) -> None:
    client = FakeClaudeClient(response_text=passing_persona_json("director"))
    enhanced = run_panel(
        core_verdict=indeterminate_core_verdict,
        manifest=sample_manifest,
        frames_dir=frames_dir,
        client=client,
    )
    assert enhanced.final_status == EnhancedStatus.INDETERMINATE
    assert enhanced.panel is None
    assert client.calls == []


def test_run_panel_all_pass(
    sample_manifest: Manifest,
    passing_core_verdict: Verdict,
    frames_dir: Path,
) -> None:
    """All 4 personas return publish_ready=true → final PASS."""
    client = FakeClaudeClient(response_text=passing_persona_json("any"))
    enhanced = run_panel(
        core_verdict=passing_core_verdict,
        manifest=sample_manifest,
        frames_dir=frames_dir,
        client=client,
    )
    assert enhanced.final_status == EnhancedStatus.PASS
    assert enhanced.panel is not None
    assert enhanced.panel.publish_ready is True
    assert len(enhanced.panel.per_persona) == 4
    # 4 personas x 1 call each = 4 client.analyze calls
    assert len(client.calls) == 4


def test_run_panel_constructs_default_client_when_none(
    sample_manifest: Manifest,
    passing_core_verdict: Verdict,
    frames_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``client`` is None, run_panel lazily builds a ClaudeVisionClient
    (ensemble.py line 50). With an empty persona list no Claude call is made,
    so this stays hermetic (no key, no network)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    enhanced = run_panel(
        core_verdict=passing_core_verdict,
        manifest=sample_manifest,
        frames_dir=frames_dir,
        client=None,
        personas=[],
    )
    assert enhanced.final_status == EnhancedStatus.PASS
    assert enhanced.panel is not None
    assert enhanced.panel.per_persona == []
    assert enhanced.panel.publish_ready is True
