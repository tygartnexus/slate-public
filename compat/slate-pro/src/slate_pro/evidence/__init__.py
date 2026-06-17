"""Compatibility shim for :mod:`slate.evidence`."""

from slate.evidence import EvidenceBundleMetadata, build_evidence_bundle, write_evidence_bundle

__all__ = [
    "EvidenceBundleMetadata",
    "build_evidence_bundle",
    "write_evidence_bundle",
]
