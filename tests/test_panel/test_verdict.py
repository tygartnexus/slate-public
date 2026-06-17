"""Tests for Panel verdict types + EnhancedVerdict composition logic."""

from __future__ import annotations

from slate.panel.verdict import (
    EnhancedStatus,
    EnhancedVerdict,
    PanelVerdict,
    PersonaFlag,
    PersonaVerdict,
)
from slate.verdict import Verdict


def _panel(publish_ready: bool, errored: bool = False) -> PanelVerdict:
    persona = PersonaVerdict(
        name="t",
        model="m",
        publish_ready=publish_ready,
        error="boom" if errored else None,
    )
    return PanelVerdict(publish_ready=publish_ready, per_persona=[persona])


def test_persona_verdict_flags_by_severity() -> None:
    p = PersonaVerdict(
        name="x",
        model="m",
        publish_ready=False,
        flags=[
            PersonaFlag(category="a", severity="critical", description="c"),
            PersonaFlag(category="b", severity="high", description="h"),
            PersonaFlag(category="c", severity="high", description="h2"),
            PersonaFlag(category="d", severity="low", description="l"),
        ],
    )
    assert len(p.flags_by_severity("critical")) == 1
    assert len(p.flags_by_severity("high")) == 2
    assert p.flags_by_severity("medium") == []


def test_enhanced_pass_when_core_pass_and_panel_publish_ready(
    passing_core_verdict: Verdict,
) -> None:
    enhanced = EnhancedVerdict.from_core_and_panel(
        passing_core_verdict, _panel(publish_ready=True)
    )
    assert enhanced.final_status == EnhancedStatus.PASS
    assert enhanced.response_quality is not None
    assert enhanced.response_quality.facts
    assert enhanced.response_quality.tradeoffs


def test_enhanced_panel_blocked_when_core_pass_but_panel_not(
    passing_core_verdict: Verdict,
) -> None:
    enhanced = EnhancedVerdict.from_core_and_panel(
        passing_core_verdict, _panel(publish_ready=False)
    )
    assert enhanced.final_status == EnhancedStatus.PANEL_BLOCKED


def test_enhanced_fail_dominates_core_fail(failing_core_verdict: Verdict) -> None:
    enhanced = EnhancedVerdict.from_core_and_panel(
        failing_core_verdict, _panel(publish_ready=True)
    )
    assert enhanced.final_status == EnhancedStatus.FAIL


def test_enhanced_indeterminate_when_core_indeterminate(
    indeterminate_core_verdict: Verdict,
) -> None:
    enhanced = EnhancedVerdict.from_core_and_panel(
        indeterminate_core_verdict, _panel(publish_ready=True)
    )
    assert enhanced.final_status == EnhancedStatus.INDETERMINATE


def test_enhanced_indeterminate_when_persona_errored(
    passing_core_verdict: Verdict,
) -> None:
    enhanced = EnhancedVerdict.from_core_and_panel(
        passing_core_verdict, _panel(publish_ready=True, errored=True)
    )
    assert enhanced.final_status == EnhancedStatus.INDETERMINATE


def test_enhanced_pass_when_no_panel_and_core_pass(
    passing_core_verdict: Verdict,
) -> None:
    enhanced = EnhancedVerdict.from_core_and_panel(passing_core_verdict, None)
    assert enhanced.final_status == EnhancedStatus.PASS
    assert enhanced.panel is None
    assert enhanced.response_quality is not None
    assert enhanced.response_quality.evidence == []
    assert enhanced.response_quality.unknowns


def test_enhanced_no_panel_core_indeterminate_is_not_publishable(
    indeterminate_core_verdict: Verdict,
) -> None:
    enhanced = EnhancedVerdict.from_core_and_panel(indeterminate_core_verdict, None)
    assert enhanced.final_status == EnhancedStatus.INDETERMINATE
    assert enhanced.response_quality is not None
    assert "Do not publish" in enhanced.response_quality.recommendation
    assert "Panel evidence was skipped" in enhanced.response_quality.risks[0]
