"""Evidence bundle generation — single-file audit artifact for a verified shot."""

from slate.evidence.bundle import (
    EvidenceBundleMetadata,
    build_evidence_bundle,
    write_evidence_bundle,
)

__all__ = [
    "EvidenceBundleMetadata",
    "build_evidence_bundle",
    "write_evidence_bundle",
]
