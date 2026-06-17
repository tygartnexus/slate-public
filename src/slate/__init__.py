"""Slate — multi-VLM verdict for rendered animation."""

__version__ = "0.1.0"

from slate.manifest import Manifest
from slate.response_quality import ResponseMode, ResponseQualityReport
from slate.verdict import Verdict, VerdictStatus

__all__ = [
    "Manifest",
    "ResponseMode",
    "ResponseQualityReport",
    "Verdict",
    "VerdictStatus",
    "__version__",
]
