"""Verdict types — what Slate returns to the caller."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from slate.response_quality import ResponseQualityReport


class VerdictStatus(str, Enum):
    """Top-level verdict status.

    * **PASS** — all configured signals passed for every analyzed frame.
    * **FAIL** — at least one hard-fail signal triggered.
    * **INDETERMINATE** — Slate could not reach a VLM provider or the provider
      returned malformed output. Treated as FAIL for publishing decisions but
      separable in audit reports so infra outages are not misread as content
      failures.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"


class SignalFailure(BaseModel):
    """One hard-fail finding from one frame, attributed to one provider."""

    model_config = ConfigDict(extra="forbid")

    signal: str
    value: Any = None
    frame: str
    provider: str
    model: str
    description: str = ""


class FrameAnalysis(BaseModel):
    """The full structured response from one provider for one frame."""

    model_config = ConfigDict(extra="allow")  # provider outputs evolve

    frame: str
    provider: str
    model: str
    raw_signals: dict[str, Any] = Field(default_factory=dict)
    quality_scores: dict[str, float] = Field(default_factory=dict)
    response_quality: ResponseQualityReport | None = None
    error: str | None = None


class Verdict(BaseModel):
    """Top-level Slate verdict for one shot."""

    model_config = ConfigDict(extra="forbid")

    status: VerdictStatus
    shot_id: str
    slate_version: str
    started_at: str
    finished_at: str
    duration_seconds: float
    providers_consulted: list[str] = Field(default_factory=list)
    frames_analyzed: list[str] = Field(default_factory=list)
    failures: list[SignalFailure] = Field(default_factory=list)
    frame_analyses: list[FrameAnalysis] = Field(default_factory=list)
    quality_scores_aggregated: dict[str, float] = Field(default_factory=dict)
    response_quality: ResponseQualityReport | None = None

    @staticmethod
    def now_iso() -> str:
        """Current UTC time as an ISO-8601 string with trailing 'Z'."""
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
