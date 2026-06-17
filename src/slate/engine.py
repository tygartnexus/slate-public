"""Verdict engine — turn provider results into a Slate Verdict.

The engine:

1. Lists and samples frames from the configured directory.
2. Calls each provider on each sampled frame.
3. Applies hard-fail rules (see :mod:`slate.signals`) to each provider result.
4. Aggregates per-frame, per-provider failures into a single :class:`Verdict`.

It does NOT decide which providers to construct — the caller passes a list.
This keeps Core open to user-supplied providers without changing engine code.
"""

from __future__ import annotations

import time
from pathlib import Path
from statistics import mean
from typing import Any

from slate import __version__
from slate.frames import list_frames, sample_frames
from slate.manifest import Manifest
from slate.providers.base import ProviderResult, VLMProvider
from slate.response_quality import (
    ResponseQualityReport,
    missing_evidence_report,
    parse_response_quality_report,
)
from slate.signals import (
    BAD_ORIENTATIONS,
    BLOCKING_SEVERITIES,
    QUALITY_KEYS,
    SIGNAL_CHARACTER_IDENTITY_MATCHES_MANIFEST,
    SIGNAL_CHARACTER_ORIENTATION,
    SIGNAL_CHARACTER_ORIENTATION_MATCHES_MOVEMENT,
    SIGNAL_CHARACTER_POSE_PLAUSIBLE,
    SIGNAL_CHARACTER_VISIBLE,
    SIGNAL_DEBUG_QUALITY_OR_BROKEN,
    SIGNAL_GROUND_CONTACT_VISIBLE,
    SIGNAL_HEAD_COVERING_OR_HAIR_PRESENT,
    SIGNAL_LANDMARK_VISIBLE,
    SIGNAL_SCALE_PLAUSIBLE,
    SIGNAL_SEVERITY,
    SIGNAL_WARDROBE_PRESENT,
)
from slate.verdict import (
    FrameAnalysis,
    SignalFailure,
    Verdict,
    VerdictStatus,
)

# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in {"true", "yes", "1"}:
            return True
        if norm in {"false", "no", "0"}:
            return False
    return None


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):  # bool is a subclass of int — guard against it
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Per-frame rule evaluation
# ---------------------------------------------------------------------------


def evaluate_frame_signals(
    frame_name: str,
    result: ProviderResult,
    manifest: Manifest,
) -> list[SignalFailure]:
    """Apply Slate's hard-fail rules to one provider's result for one frame."""
    failures: list[SignalFailure] = []
    if not result.ok:
        # Infra failure → surface as a single signal failure so the verdict
        # can report INDETERMINATE distinctly from content failures.
        failures.append(
            SignalFailure(
                signal="__provider_error__",
                value=result.error,
                frame=frame_name,
                provider=result.provider,
                model=result.model,
                description=result.error or "",
            )
        )
        return failures

    signals = result.signals
    desc = str(signals.get("description", ""))
    char = manifest.primary_character()

    if _as_bool(signals.get(SIGNAL_DEBUG_QUALITY_OR_BROKEN)) is True:
        failures.append(_fail(SIGNAL_DEBUG_QUALITY_OR_BROKEN, True, frame_name, result, desc))

    if char and char.must_be_visible and _as_bool(signals.get(SIGNAL_CHARACTER_VISIBLE)) is not True:
        failures.append(_fail(SIGNAL_CHARACTER_VISIBLE, False, frame_name, result, desc))

    if manifest.expected_landmarks and _as_bool(signals.get(SIGNAL_LANDMARK_VISIBLE)) is False:
        failures.append(_fail(SIGNAL_LANDMARK_VISIBLE, False, frame_name, result, desc))

    if char and char.must_be_upright:
        orient = str(signals.get(SIGNAL_CHARACTER_ORIENTATION, "")).strip().lower()
        if orient in BAD_ORIENTATIONS:
            failures.append(_fail(SIGNAL_CHARACTER_ORIENTATION, orient, frame_name, result, desc))

    if _as_bool(signals.get(SIGNAL_CHARACTER_POSE_PLAUSIBLE)) is False:
        failures.append(_fail(SIGNAL_CHARACTER_POSE_PLAUSIBLE, False, frame_name, result, desc))

    if char and char.must_have_ground_contact and _as_bool(signals.get(SIGNAL_GROUND_CONTACT_VISIBLE)) is False:
        failures.append(
            _fail(SIGNAL_GROUND_CONTACT_VISIBLE, False, frame_name, result, desc)
        )

    if _as_bool(signals.get(SIGNAL_SCALE_PLAUSIBLE)) is False:
        failures.append(_fail(SIGNAL_SCALE_PLAUSIBLE, False, frame_name, result, desc))

    if _as_bool(signals.get(SIGNAL_CHARACTER_ORIENTATION_MATCHES_MOVEMENT)) is False:
        failures.append(
            _fail(SIGNAL_CHARACTER_ORIENTATION_MATCHES_MOVEMENT, False, frame_name, result, desc)
        )

    if char and char.must_have_wardrobe and _as_bool(signals.get(SIGNAL_WARDROBE_PRESENT)) is not True:
        failures.append(_fail(SIGNAL_WARDROBE_PRESENT, False, frame_name, result, desc))

    if char and char.must_have_hair_or_head_covering and _as_bool(signals.get(SIGNAL_HEAD_COVERING_OR_HAIR_PRESENT)) is not True:
        failures.append(
            _fail(SIGNAL_HEAD_COVERING_OR_HAIR_PRESENT, False, frame_name, result, desc)
        )

    if char and char.must_match_identity and _as_bool(signals.get(SIGNAL_CHARACTER_IDENTITY_MATCHES_MANIFEST)) is not True:
        failures.append(
            _fail(SIGNAL_CHARACTER_IDENTITY_MATCHES_MANIFEST, False, frame_name, result, desc)
        )

    severity = str(signals.get(SIGNAL_SEVERITY, "")).strip().lower()
    if severity in BLOCKING_SEVERITIES:
        failures.append(_fail(SIGNAL_SEVERITY, severity, frame_name, result, desc))

    thresholds = manifest.quality_thresholds.thresholds()
    for axis, threshold in thresholds.items():
        val = _as_number(signals.get(axis))
        if val is not None and val < threshold:
            failures.append(
                SignalFailure(
                    signal=axis,
                    value=val,
                    frame=frame_name,
                    provider=result.provider,
                    model=result.model,
                    description=f"{axis}={val:g} below threshold {threshold}. {desc}",
                )
            )

    return failures


def _fail(
    signal: str, value: Any, frame_name: str, result: ProviderResult, desc: str
) -> SignalFailure:
    return SignalFailure(
        signal=signal,
        value=value,
        frame=frame_name,
        provider=result.provider,
        model=result.model,
        description=desc,
    )


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------


def verify(
    *,
    manifest: Manifest,
    frames_dir: Path,
    providers: list[VLMProvider],
) -> Verdict:
    """Run the verdict engine end-to-end and return a :class:`Verdict`."""
    started = time.monotonic()
    started_iso = Verdict.now_iso()

    all_frames = list_frames(frames_dir)
    sampled = sample_frames(all_frames, manifest.frame_sampling)

    failures: list[SignalFailure] = []
    analyses: list[FrameAnalysis] = []
    quality_buckets: dict[str, list[float]] = {k: [] for k in QUALITY_KEYS}
    saw_provider_error = False
    saw_response_quality_error = False

    for frame_path in sampled:
        for provider in providers:
            result = provider.analyze_frame(frame_path, manifest)
            frame_failures = evaluate_frame_signals(frame_path.name, result, manifest)
            failures.extend(frame_failures)
            if not result.ok:
                saw_provider_error = True
            response_quality = parse_response_quality_report(result.signals)
            raw_signals = dict(result.signals)
            if response_quality is not None:
                raw_signals["response_quality"] = response_quality.model_dump()
            if result.ok and response_quality is None:
                saw_response_quality_error = True
                failures.append(
                    SignalFailure(
                        signal="__response_quality_missing__",
                        value=None,
                        frame=frame_path.name,
                        provider=result.provider,
                        model=result.model,
                        description=(
                            "Provider output omitted a valid response_quality object."
                        ),
                    )
                )

            qscores: dict[str, float] = {}
            for qk in QUALITY_KEYS:
                val = _as_number(result.signals.get(qk))
                if val is not None:
                    qscores[qk] = val
                    quality_buckets[qk].append(val)

            analyses.append(
                FrameAnalysis(
                    frame=frame_path.name,
                    provider=result.provider,
                    model=result.model,
                    raw_signals=raw_signals,
                    quality_scores=qscores,
                    response_quality=response_quality,
                    error=result.error,
                )
            )

    content_failures = [
        f
        for f in failures
        if f.signal not in {"__provider_error__", "__response_quality_missing__"}
    ]
    if content_failures:
        status = VerdictStatus.FAIL
    elif saw_provider_error or saw_response_quality_error:
        status = VerdictStatus.INDETERMINATE
    else:
        status = VerdictStatus.PASS

    aggregated = {k: mean(vs) for k, vs in quality_buckets.items() if vs}
    response_quality = _build_verdict_response_quality(
        status=status,
        providers_consulted=sorted({a.provider for a in analyses}),
        frames_analyzed=[f.name for f in sampled],
        failures=failures,
        analyses=analyses,
        saw_provider_error=saw_provider_error,
        saw_response_quality_error=saw_response_quality_error,
    )

    finished = time.monotonic()
    return Verdict(
        status=status,
        shot_id=manifest.shot_id,
        slate_version=__version__,
        started_at=started_iso,
        finished_at=Verdict.now_iso(),
        duration_seconds=round(finished - started, 3),
        providers_consulted=sorted({a.provider for a in analyses}),
        frames_analyzed=[f.name for f in sampled],
        failures=failures,
        frame_analyses=analyses,
        quality_scores_aggregated=aggregated,
        response_quality=response_quality,
    )


def _build_verdict_response_quality(
    *,
    status: VerdictStatus,
    providers_consulted: list[str],
    frames_analyzed: list[str],
    failures: list[SignalFailure],
    analyses: list[FrameAnalysis],
    saw_provider_error: bool,
    saw_response_quality_error: bool,
) -> ResponseQualityReport:
    """Summarize the verified run into the shared response-quality contract."""
    if not analyses:
        return missing_evidence_report(
            facts=[f"Slate reached status {status.value} without frame analyses."],
            recommendation="Do not treat this verdict as verified.",
            confidence_score=0.2,
            unknown="No provider analyses were recorded.",
            risk="A missing analysis set can make an unsupported verdict look authoritative.",
        )

    provider_quality_count = sum(1 for analysis in analyses if analysis.response_quality)
    facts = [
        f"Slate status is {status.value}.",
        f"Analyzed {len(frames_analyzed)} sampled frame(s).",
        f"Consulted provider(s): {', '.join(providers_consulted) or '(none)'}.",
        f"Recorded {len(failures)} hard-fail finding(s).",
    ]
    evidence = [
        f"frames_analyzed={frames_analyzed}",
        f"providers_consulted={providers_consulted}",
        f"failure_signals={[failure.signal for failure in failures]}",
    ]
    unknowns = [
        "Unsampled frames were not inspected by this verdict.",
        "Ground truth beyond the manifest and sampled pixels was not independently verified.",
    ]
    if provider_quality_count < len(analyses):
        unknowns.append(
            "One or more provider outputs omitted a valid response_quality object."
        )
    if saw_provider_error:
        unknowns.append("At least one provider call failed.")

    risks = [
        "A PASS can miss issues outside sampled frames or outside the configured signal taxonomy.",
        "Provider judgments can be wrong or inconsistent on ambiguous visual evidence.",
    ]
    counterarguments = [
        "Multiple providers or sampled frames can increase confidence when their evidence agrees.",
        "A hard-fail signal is still useful even when the exact creative severity needs human review.",
    ]

    if status == VerdictStatus.PASS:
        recommendation = "Treat the shot as passing automated checks, but keep human review for high-stakes publishing."
        confidence = 0.78 if not saw_provider_error else 0.58
    elif status == VerdictStatus.FAIL:
        recommendation = "Do not publish until the listed hard-fail findings are reviewed and resolved."
        confidence = 0.82 if not saw_provider_error else 0.68
    else:
        if saw_response_quality_error and not saw_provider_error:
            recommendation = "Do not publish based on this run; require providers to return response_quality and rerun."
        else:
            recommendation = "Do not publish based on this run; fix provider/runtime evidence gaps and rerun."
        confidence = 0.35

    return ResponseQualityReport(
        facts=facts,
        assumptions=[
            "The manifest describes the intended shot accurately.",
            "The sampled frames are representative of the render segment being judged.",
        ],
        unknowns=unknowns,
        confidence_score=confidence,
        evidence=evidence,
        risks=risks,
        counterarguments=counterarguments,
        recommendation=recommendation,
        tradeoffs=[
            "More frames and providers improve evidence but increase latency and cost.",
            "Strict failure handling may block borderline shots that a human would accept.",
        ],
        what_would_change_recommendation=[
            "A rerun with additional frames or providers that changes the failure set.",
            "Human review showing the flagged issue is intentional or visually acceptable.",
            "A corrected manifest that changes the expected character, landmarks, or thresholds.",
        ],
    )
