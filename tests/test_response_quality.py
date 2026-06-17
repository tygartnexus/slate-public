"""Tests for the reusable response-quality contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from slate.response_quality import (
    PROMPT_TEMPLATES,
    REQUIRED_SECTION_KEYS,
    ResponseMode,
    ResponseQualityReport,
    build_response_quality_prompt,
    missing_evidence_report,
    missing_required_sections,
    parse_response_quality_report,
)


def _report() -> ResponseQualityReport:
    return ResponseQualityReport(
        facts=["The frame was analyzed."],
        assumptions=["The manifest is accurate."],
        unknowns=["No human review was attached."],
        confidence_score=0.72,
        evidence=["frame_0000.png was sampled."],
        risks=["Unsampled frames may differ."],
        counterarguments=["The sampled frame may still be representative."],
        recommendation="Proceed only after review.",
        tradeoffs=["More evidence costs more runtime."],
        what_would_change_recommendation=["A human review finding a blocker."],
    )


def test_report_contains_required_sections() -> None:
    dumped = _report().model_dump()
    assert set(REQUIRED_SECTION_KEYS).issubset(dumped)


def test_confidence_score_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ResponseQualityReport(
            facts=[],
            assumptions=[],
            unknowns=[],
            confidence_score=1.5,
            evidence=[],
            risks=[],
            counterarguments=[],
            recommendation="invalid",
            tradeoffs=[],
            what_would_change_recommendation=[],
        )


def test_missing_required_sections_lists_absent_keys() -> None:
    assert missing_required_sections({"facts": []}) == list(REQUIRED_SECTION_KEYS[1:])


def test_missing_evidence_report_acknowledges_gap() -> None:
    report = missing_evidence_report(
        facts=["Provider returned malformed JSON."],
        recommendation="Rerun with valid output.",
        confidence_score=0.2,
        unknown="Evidence is missing.",
        risk="Unsupported output could be treated as verified.",
    )
    assert report.evidence == []
    assert "Evidence is missing." in report.unknowns
    assert report.tradeoffs


def test_parse_response_quality_normalizes_scalar_list_sections() -> None:
    parsed = parse_response_quality_report(
        {
            "response_quality": {
                "facts": "The frame was analyzed.",
                "assumptions": "The manifest is accurate.",
                "unknowns": "No human review was attached.",
                "confidence_score": 0.72,
                "evidence": "frame_0000.png was sampled.",
                "risks": "Unsampled frames may differ.",
                "counterarguments": "The sampled frame may still be representative.",
                "recommendation": "Proceed only after review.",
                "tradeoffs": "More evidence costs more runtime.",
                "what_would_change_recommendation": "A human review finding a blocker.",
            }
        }
    )

    assert parsed is not None
    assert parsed.facts == ["The frame was analyzed."]
    assert parsed.what_would_change_recommendation == [
        "A human review finding a blocker."
    ]


def test_all_modes_emit_required_response_quality_shape() -> None:
    for mode in ResponseMode:
        prompt = build_response_quality_prompt(mode=mode, subject="test output")
        assert "response_quality" in prompt
        for key in REQUIRED_SECTION_KEYS:
            assert f'"{key}"' in prompt


def test_prompt_templates_are_centralized_and_complete() -> None:
    expected = {
        "anti_hallucination",
        "red_team_review",
        "ceo_reality_check",
        "evidence_based_recommendation",
        "legal_compliance_review",
        "technical_architecture_review",
        "bias_detection",
        "executive_decision_matrix",
    }
    assert expected == set(PROMPT_TEMPLATES)
    assert all("TODO" not in value and "TBD" not in value for value in PROMPT_TEMPLATES.values())
