"""Compatibility shim for :mod:`slate.evidence.bundle`."""

from slate.evidence.bundle import (
    DEFAULT_THUMBNAIL_PX,
    EvidenceBundleMetadata,
    build_evidence_bundle,
    write_evidence_bundle,
)

__all__ = [
    "DEFAULT_THUMBNAIL_PX",
    "EvidenceBundleMetadata",
    "build_evidence_bundle",
    "write_evidence_bundle",
]
