"""Verdict types for the Panel persona ensemble.

Panel produces structured critique from multiple expert personas. Each persona
returns a :class:`PersonaVerdict` containing flags by severity. The ensemble
fuses these into a :class:`PanelVerdict`, which is then combined with Core's
:class:`slate.verdict.Verdict` into an :class:`EnhancedVerdict` carrying the
final publish decision.

The four severities are intentionally coarse — fine-grained scoring is what
Core's quality axes already provide.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from slate.response_quality import ResponseQualityReport, missing_evidence_report
from slate.verdict import Verdict, VerdictStatus

Severity = Literal["critical", "high", "medium", "low"]


class EnhancedStatus(str, Enum):
    """Final publish status combining Core + Panel.

    * **PASS** — Core PASS and every persona is publish_ready.
    * **FAIL** — Core FAIL (Panel may not have run).
    * **PANEL_BLOCKED** — Core PASS but at least one persona flagged critical
      OR returned publish_ready=False.
    * **INDETERMINATE** — Core INDETERMINATE or any provider/persona errored.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    PANEL_BLOCKED = "PANEL_BLOCKED"
    INDETERMINATE = "INDETERMINATE"


class PersonaFlag(BaseModel):
    """One observation from one persona about one frame."""

    model_config = ConfigDict(extra="forbid")

    category: str
    severity: Severity
    frame: str | None = None
    description: str


class PersonaVerdict(BaseModel):
    """One persona's full evaluation of the sampled frames."""

    model_config = ConfigDict(extra="forbid")

    name: str
    model: str
    publish_ready: bool
    summary: str = ""
    flags: list[PersonaFlag] = Field(default_factory=list)
    per_frame_notes: dict[str, str] = Field(default_factory=dict)
    response_quality: ResponseQualityReport | None = None
    raw_response: str = ""  # full unparsed response, for evidence bundles
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def flags_by_severity(self, severity: Severity) -> list[PersonaFlag]:
        return [f for f in self.flags if f.severity == severity]


class PanelVerdict(BaseModel):
    """The fused ensemble result."""

    model_config = ConfigDict(extra="forbid")

    publish_ready: bool
    per_persona: list[PersonaVerdict] = Field(default_factory=list)
    fused_critical_flags: list[PersonaFlag] = Field(default_factory=list)
    fused_high_flags: list[PersonaFlag] = Field(default_factory=list)
    summary: str = ""
    duration_seconds: float = 0.0
    slate_version: str = ""
    response_quality: ResponseQualityReport | None = None


class EnhancedVerdict(BaseModel):
    """Final wrapper combining Core verdict + Panel verdict.

    `final_status` is the single source of truth for publish decisions —
    callers should NOT separately consult `core.status`.
    """

    model_config = ConfigDict(extra="forbid")

    final_status: EnhancedStatus
    core: Verdict
    panel: PanelVerdict | None = None
    response_quality: ResponseQualityReport | None = None

    @classmethod
    def from_core_and_panel(
        cls, core: Verdict, panel: PanelVerdict | None
    ) -> EnhancedVerdict:
        """Combine a Core verdict and (optionally) a Panel verdict into final status."""
        if core.status == VerdictStatus.FAIL:
            final = EnhancedStatus.FAIL
        elif core.status == VerdictStatus.INDETERMINATE:
            final = EnhancedStatus.INDETERMINATE
        elif panel is None:
            final = EnhancedStatus.PASS
        elif any(p.error for p in panel.per_persona):
            final = EnhancedStatus.INDETERMINATE
        elif panel.publish_ready:
            final = EnhancedStatus.PASS
        else:
            final = EnhancedStatus.PANEL_BLOCKED
        return cls(
            final_status=final,
            core=core,
            panel=panel,
            response_quality=_enhanced_response_quality(core, panel, final),
        )


def _enhanced_response_quality(
    core: Verdict, panel: PanelVerdict | None, final: EnhancedStatus
) -> ResponseQualityReport:
    if panel is None:
        return missing_evidence_report(
            facts=[
                f"Core status is {core.status.value}.",
                f"Enhanced final status is {final.value}.",
            ],
            recommendation=_panel_missing_recommendation(core.status),
            confidence_score=_panel_missing_confidence(core.status),
            unknown="Panel persona evidence was not produced.",
            risk=_panel_missing_risk(core.status),
        )

    errored = [persona.name for persona in panel.per_persona if persona.error]
    critical_count = len(panel.fused_critical_flags)
    high_count = len(panel.fused_high_flags)
    return ResponseQualityReport(
        facts=[
            f"Core status is {core.status.value}.",
            f"Panel publish_ready is {panel.publish_ready}.",
            f"Enhanced final status is {final.value}.",
            f"Panel recorded {critical_count} critical flag(s) and {high_count} high flag(s).",
        ],
        assumptions=[
            "Persona outputs reflect the sampled frames they reviewed.",
            "The Core manifest accurately describes the intended shot.",
        ],
        unknowns=[
            "Unsampled frames and off-manifest creative intent were not fully reviewed.",
            *(
                [f"Errored persona(s) produced incomplete evidence: {', '.join(errored)}."]
                if errored
                else []
            ),
        ],
        confidence_score=0.86 if final in {EnhancedStatus.FAIL, EnhancedStatus.PANEL_BLOCKED} else 0.74,
        evidence=[
            f"core_failures={len(core.failures)}",
            f"persona_count={len(panel.per_persona)}",
            f"panel_summary={panel.summary}",
        ],
        risks=[
            "Persona judgments can over-block stylistic choices when context is incomplete.",
            "A passing panel can still miss issues outside sampled frames.",
        ],
        counterarguments=[
            "Independent persona agreement increases confidence in publish readiness.",
            "Core hard-fail signals remain useful even when panel evidence is incomplete.",
        ],
        recommendation=_recommendation_for(final),
        tradeoffs=[
            "Panel review increases review depth but adds model cost and latency.",
            "Conservative blocking protects quality but can slow iteration on acceptable shots.",
        ],
        what_would_change_recommendation=[
            "A rerun with valid evidence from errored personas.",
            "Additional frame samples changing the critical/high flag set.",
            "Human review confirming a flagged issue is intentional and acceptable.",
        ],
    )


def _recommendation_for(final: EnhancedStatus) -> str:
    if final == EnhancedStatus.PASS:
        return "Treat as passing automated Core and Panel checks, with human review for high-stakes publication."
    if final == EnhancedStatus.PANEL_BLOCKED:
        return "Do not publish until Panel blocking findings are reviewed or corrected."
    if final == EnhancedStatus.FAIL:
        return "Do not publish until Core hard-fail findings are resolved."
    return "Do not publish from this run; fix indeterminate provider/persona evidence and rerun."


def _panel_missing_recommendation(status: VerdictStatus) -> str:
    if status == VerdictStatus.PASS:
        return (
            "Treat this as a Core-only pass; run Panel before relying on "
            "subjective publish readiness."
        )
    if status == VerdictStatus.FAIL:
        return "Do not publish until Core hard-fail findings are resolved."
    return "Do not publish from this run; fix Core evidence gaps and rerun before Panel."


def _panel_missing_confidence(status: VerdictStatus) -> float:
    if status == VerdictStatus.PASS:
        return 0.55
    if status == VerdictStatus.FAIL:
        return 0.65
    return 0.35


def _panel_missing_risk(status: VerdictStatus) -> str:
    if status == VerdictStatus.PASS:
        return "A Core-only PASS can miss subjective or motion-quality issues Panel is designed to catch."
    if status == VerdictStatus.FAIL:
        return "Panel evidence was skipped, but Core hard-fail findings are already publish-blocking."
    return "Panel evidence was skipped because Core evidence was incomplete or invalid."
