"""Reusable response-quality contract for Slate AI outputs.

The contract keeps model and system conclusions separated into facts,
assumptions, unknowns, evidence, risks, counterarguments, recommendations,
tradeoffs, and confidence. It is intentionally plain data so Slate's provider,
Panel, and dashboard surfaces can share the same JSON shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ResponseMode(str, Enum):
    """Supported output/review modes."""

    STANDARD = "standard"
    EVIDENCE_BASED = "evidence_based"
    RED_TEAM = "red_team"
    EXECUTIVE_MEMO = "executive_memo"
    TECHNICAL_REVIEW = "technical_review"
    LEGAL_RISK_REVIEW = "legal_risk_review"


REQUIRED_SECTION_KEYS: tuple[str, ...] = (
    "facts",
    "assumptions",
    "unknowns",
    "confidence_score",
    "evidence",
    "risks",
    "counterarguments",
    "recommendation",
    "tradeoffs",
    "what_would_change_recommendation",
)


PROMPT_TEMPLATES: dict[str, str] = {
    "anti_hallucination": (
        "Do not invent facts. If evidence is missing, say exactly what is "
        "missing and lower confidence."
    ),
    "red_team_review": (
        "Lead with the strongest ways this conclusion can fail. Identify "
        "unsupported claims, operational risks, and counterarguments."
    ),
    "ceo_reality_check": (
        "Frame the answer as a decision under uncertainty. Separate verified "
        "facts from assumptions and state the business tradeoffs."
    ),
    "evidence_based_recommendation": (
        "Make a recommendation only after listing evidence, assumptions, "
        "unknowns, risks, counterarguments, and what would change the answer."
    ),
    "legal_compliance_review": (
        "Do not present legal conclusions as attorney advice. Identify "
        "compliance issues, source limits, missing jurisdiction facts, and "
        "controls for counsel or owner review."
    ),
    "technical_architecture_review": (
        "Ground the review in verified behavior, architecture facts, failure "
        "modes, validation status, and operational risk."
    ),
    "bias_detection": (
        "Look for framing bias, omitted alternatives, overconfident language, "
        "and asymmetric treatment of evidence."
    ),
    "executive_decision_matrix": (
        "Compare options by evidence, confidence, upside, downside, reversibility, "
        "cost, and evidence that would change the decision."
    ),
}


MODE_TEMPLATES: dict[ResponseMode, str] = {
    ResponseMode.STANDARD: (
        "Give a direct answer, but include assumptions and confidence whenever "
        "the answer depends on incomplete evidence."
    ),
    ResponseMode.EVIDENCE_BASED: PROMPT_TEMPLATES["evidence_based_recommendation"],
    ResponseMode.RED_TEAM: PROMPT_TEMPLATES["red_team_review"],
    ResponseMode.EXECUTIVE_MEMO: PROMPT_TEMPLATES["ceo_reality_check"],
    ResponseMode.TECHNICAL_REVIEW: PROMPT_TEMPLATES["technical_architecture_review"],
    ResponseMode.LEGAL_RISK_REVIEW: PROMPT_TEMPLATES["legal_compliance_review"],
}


class ResponseQualityReport(BaseModel):
    """Required quality sections for any AI-generated judgment."""

    model_config = ConfigDict(extra="forbid")

    facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    counterarguments: list[str] = Field(default_factory=list)
    recommendation: str
    tradeoffs: list[str] = Field(default_factory=list)
    what_would_change_recommendation: list[str] = Field(default_factory=list)


def build_response_quality_prompt(
    *,
    mode: ResponseMode = ResponseMode.EVIDENCE_BASED,
    subject: str = "this output",
) -> str:
    """Return prompt text that forces the shared response-quality JSON object."""
    template = MODE_TEMPLATES[mode]
    section_lines = "\n".join(f'    "{key}": ...,' for key in REQUIRED_SECTION_KEYS)
    return (
        "AI RESPONSE QUALITY CONTRACT\n"
        f"Mode: {mode.value}\n"
        f"Subject: {subject}\n"
        f"{template}\n"
        f"{PROMPT_TEMPLATES['anti_hallucination']}\n"
        f"{PROMPT_TEMPLATES['bias_detection']}\n"
        "\n"
        "Your JSON MUST include a top-level `response_quality` object with every "
        "required section. Use arrays for list sections. Use confidence_score "
        "from 0.0 to 1.0. If evidence is missing, put that in `unknowns` and "
        "`what_would_change_recommendation`; do not fill gaps with guesses.\n"
        "\n"
        "Required shape:\n"
        '  "response_quality": {\n'
        f"{section_lines}\n"
        "  }\n"
    )


def missing_required_sections(raw: Mapping[str, Any]) -> list[str]:
    """Return required section keys missing from a raw response-quality object."""
    return [key for key in REQUIRED_SECTION_KEYS if key not in raw]


def parse_response_quality_report(raw: Mapping[str, Any]) -> ResponseQualityReport | None:
    """Parse a nested response_quality object from a model/provider payload."""
    candidate = raw.get("response_quality")
    if not isinstance(candidate, Mapping):
        return None
    try:
        return ResponseQualityReport.model_validate(candidate)
    except ValidationError:
        return None


def missing_evidence_report(
    *,
    facts: list[str],
    recommendation: str,
    confidence_score: float,
    unknown: str,
    risk: str,
) -> ResponseQualityReport:
    """Build an explicit low-evidence report for failures or omitted sections."""
    return ResponseQualityReport(
        facts=facts,
        assumptions=["The available system metadata is accurate."],
        unknowns=[unknown],
        confidence_score=confidence_score,
        evidence=[],
        risks=[risk],
        counterarguments=[
            "The underlying content may still be acceptable if independent evidence supports it."
        ],
        recommendation=recommendation,
        tradeoffs=[
            "Blocking or rechecking costs time, but avoids presenting unsupported output as verified."
        ],
        what_would_change_recommendation=[
            "A valid response_quality object with concrete evidence/citations.",
            "Independent human or tool verification of the disputed output.",
        ],
    )
