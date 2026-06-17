"""Fusion logic — combine N PersonaVerdicts into one PanelVerdict.

Rules (v1):
* ANY critical flag from ANY persona → PanelVerdict.publish_ready = False.
* 2+ high flags from the SAME persona → PanelVerdict.publish_ready = False.
* ANY persona returning publish_ready=False → publish_ready = False.
* Otherwise → publish_ready = True.

The fused critical / high lists collect every critical / high flag across
personas so callers can present a single sorted list rather than digging into
per-persona structures.
"""

from __future__ import annotations

from slate.panel.verdict import PanelVerdict, PersonaFlag, PersonaVerdict
from slate.response_quality import ResponseQualityReport


def fuse(
    per_persona: list[PersonaVerdict], *, slate_version: str, duration_seconds: float
) -> PanelVerdict:
    """Combine persona verdicts. Pure function over the persona outputs."""
    critical: list[PersonaFlag] = []
    high: list[PersonaFlag] = []
    publish_ready = True
    reasons: list[str] = []

    for persona in per_persona:
        if not persona.ok:
            # A failed persona contributes neither flags nor a publish vote;
            # the engine surfaces this as INDETERMINATE at the EnhancedVerdict
            # layer, not here.
            continue

        if not persona.publish_ready:
            publish_ready = False
            reasons.append(f"{persona.name} returned publish_ready=false")

        p_critical = persona.flags_by_severity("critical")
        p_high = persona.flags_by_severity("high")
        critical.extend(p_critical)
        high.extend(p_high)

        if p_critical:
            publish_ready = False
            reasons.append(
                f"{persona.name} raised {len(p_critical)} critical flag(s)"
            )
        if len(p_high) >= 2:
            publish_ready = False
            reasons.append(
                f"{persona.name} raised {len(p_high)} high flags (2+ rule)"
            )

    summary = _summarize(per_persona, publish_ready, reasons)

    return PanelVerdict(
        publish_ready=publish_ready,
        per_persona=per_persona,
        fused_critical_flags=critical,
        fused_high_flags=high,
        summary=summary,
        slate_version=slate_version,
        duration_seconds=duration_seconds,
        response_quality=_build_response_quality(
            per_persona=per_persona,
            publish_ready=publish_ready,
            critical=critical,
            high=high,
            summary=summary,
        ),
    )


def _summarize(
    per_persona: list[PersonaVerdict], publish_ready: bool, reasons: list[str]
) -> str:
    healthy = [p for p in per_persona if p.ok]
    errored = [p for p in per_persona if not p.ok]
    parts: list[str] = []
    if healthy:
        votes = ", ".join(
            f"{p.name}={'PASS' if p.publish_ready else 'BLOCK'}" for p in healthy
        )
        parts.append(votes)
    if errored:
        parts.append(f"errored: {', '.join(p.name for p in errored)}")
    if not publish_ready and reasons:
        parts.append(reasons[0])
    return " | ".join(parts) if parts else "(no personas ran)"


def _build_response_quality(
    *,
    per_persona: list[PersonaVerdict],
    publish_ready: bool,
    critical: list[PersonaFlag],
    high: list[PersonaFlag],
    summary: str,
) -> ResponseQualityReport:
    errored = [p.name for p in per_persona if p.error]
    missing_quality = [p.name for p in per_persona if p.response_quality is None]
    return ResponseQualityReport(
        facts=[
            f"Panel publish_ready is {publish_ready}.",
            f"Evaluated {len(per_persona)} persona output(s).",
            f"Found {len(critical)} critical flag(s) and {len(high)} high flag(s).",
        ],
        assumptions=[
            "Each persona reviewed the same sampled frames.",
            "Each persona's criteria match its declared professional viewpoint.",
        ],
        unknowns=[
            "The panel did not review unsampled frames.",
            *(
                [f"Errored persona(s): {', '.join(errored)}."]
                if errored
                else []
            ),
            *(
                [f"Persona(s) missing valid response_quality: {', '.join(missing_quality)}."]
                if missing_quality
                else []
            ),
        ],
        confidence_score=0.62 if errored or missing_quality else 0.82,
        evidence=[
            f"summary={summary}",
            f"critical_categories={[flag.category for flag in critical]}",
            f"high_categories={[flag.category for flag in high]}",
        ],
        risks=[
            "Panel may over-index on visible sampled frames and miss motion between samples.",
            "Subjective persona criteria can flag intentional style as a defect.",
        ],
        counterarguments=[
            "Diverse persona criteria reduce the chance of a single-model blind spot.",
            "Critical flags are useful even when final severity needs human confirmation.",
        ],
        recommendation=_recommendation(
            publish_ready=publish_ready,
            errored=errored,
        ),
        tradeoffs=[
            "More personas provide broader critique but increase cost and latency.",
            "Strict panel blocking catches defects earlier but can slow creative iteration.",
        ],
        what_would_change_recommendation=[
            "Additional sampled frames changing the critical or high flag set.",
            "Human review confirming a flagged item is intentional.",
            "A rerun where errored or incomplete personas return valid evidence.",
        ],
    )


def _recommendation(*, publish_ready: bool, errored: list[str]) -> str:
    if errored:
        return (
            "Do not publish from this Panel result; rerun after fixing errored "
            f"persona evidence: {', '.join(errored)}."
        )
    if not publish_ready:
        return "Do not publish until critical/high panel concerns are reviewed."
    return "Treat the panel as passing, subject to final human review."
