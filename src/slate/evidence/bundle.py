"""Evidence bundle writer.

Produces a single ``.tar.gz`` that records what Slate evaluated, when, how, and
what each VLM provider and Panel persona said. Full frame bytes are not embedded
by default; SHA-256 hashes anchor the analyzed frames. Optional thumbnails are
visual derivatives and should be enabled only when the bundle is safe to share.
For external sharing, ``redact_raw_outputs`` removes raw provider-output files
and replaces raw provider/persona fields in the verdict copy.

Bundle layout::

    <bundle>.tar.gz
      ├── verdict.json                   # EnhancedVerdict (or Core Verdict)
      ├── response_quality.json          # top-level quality contract summary
      ├── manifest.json                  # the Slate manifest used
      ├── environment.json               # versions, models, timestamps, platform
      ├── frame_hashes.json              # SHA-256 of every analyzed frame
      ├── redaction.json                 # present only when raw outputs redacted
      ├── provider_outputs/
      │   ├── gemma.json
      │   └── nvidia-primary.json
      ├── panel/
      │   ├── director.json              # full PersonaVerdict + raw response
      │   ├── color_grader.json
      │   ├── animator.json
      │   └── audience.json
      └── thumbnails/                    # opt-in, 256-px JPEGs
          ├── frame_0000.jpg
          ├── frame_0360.jpg
          └── frame_0719.jpg
"""

from __future__ import annotations

import hashlib
import io
import json
import platform
import sys
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slate import __version__ as SLATE_VERSION  # noqa: N812
from slate.panel.verdict import EnhancedVerdict
from slate.verdict import Verdict

DEFAULT_THUMBNAIL_PX = 256


@dataclass(frozen=True)
class EvidenceBundleMetadata:
    """Environment + run metadata captured at bundle time."""

    bundle_created_at: str
    slate_version: str
    python_version: str
    platform: str
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_created_at": self.bundle_created_at,
            "slate_version": self.slate_version,
            "python_version": self.python_version,
            "platform": self.platform,
            **self.extras,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_thumbnail(frame_path: Path, max_px: int) -> bytes:
    from PIL import Image  # local import — PIL only needed when thumbnails enabled

    img: Image.Image = Image.open(frame_path)
    img.thumbnail((max_px, max_px))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Build (in-memory) and write (to disk)
# ---------------------------------------------------------------------------


def build_evidence_bundle(
    *,
    verdict: EnhancedVerdict | Verdict,
    manifest_path: Path,
    frames_dir: Path,
    include_thumbnails: bool = False,
    redact_raw_outputs: bool = False,
    thumbnail_px: int = DEFAULT_THUMBNAIL_PX,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, bytes]:
    """Build the bundle as a name -> bytes dict (no disk write yet)."""
    metadata = EvidenceBundleMetadata(
        bundle_created_at=_now_iso(),
        slate_version=SLATE_VERSION,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        extras=extra_metadata or {},
    )

    core_verdict = verdict.core if isinstance(verdict, EnhancedVerdict) else verdict

    files: dict[str, bytes] = {}
    files["verdict.json"] = json.dumps(
        _verdict_dump(verdict, redact_raw_outputs=redact_raw_outputs), indent=2
    ).encode("utf-8")
    response_quality = getattr(verdict, "response_quality", None)
    if response_quality is not None:
        files["response_quality.json"] = response_quality.model_dump_json(indent=2).encode(
            "utf-8"
        )
    files["manifest.json"] = manifest_path.read_bytes()
    files["environment.json"] = json.dumps(metadata.to_dict(), indent=2).encode("utf-8")

    # Frame hashes anchor what was analyzed without embedding frame bytes.
    frame_hashes: dict[str, str] = {}
    for name in core_verdict.frames_analyzed:
        frame_path = frames_dir / name
        if frame_path.is_file():
            frame_hashes[name] = _hash_file(frame_path)
    files["frame_hashes.json"] = json.dumps(frame_hashes, indent=2).encode("utf-8")

    # Per-provider raw outputs from the Core run.
    if redact_raw_outputs:
        files["redaction.json"] = json.dumps(_redaction_manifest(), indent=2).encode(
            "utf-8"
        )
    else:
        provider_dump: dict[str, list[dict[str, Any]]] = {}
        for analysis in core_verdict.frame_analyses:
            provider_dump.setdefault(analysis.provider, []).append(
                analysis.model_dump(mode="json")
            )
        for provider_name, entries in provider_dump.items():
            files[f"provider_outputs/{provider_name}.json"] = json.dumps(
                entries, indent=2
            ).encode("utf-8")

    # Panel — one file per persona, including the raw Claude response text.
    if isinstance(verdict, EnhancedVerdict) and verdict.panel is not None:
        if verdict.panel.response_quality is not None:
            files["panel/response_quality.json"] = verdict.panel.response_quality.model_dump_json(
                indent=2
            ).encode("utf-8")
        for persona in verdict.panel.per_persona:
            persona_dump = persona.model_dump(mode="json")
            if redact_raw_outputs:
                persona_dump["raw_response"] = "[redacted]"
            files[f"panel/{persona.name}.json"] = json.dumps(
                persona_dump, indent=2
            ).encode("utf-8")

    # Optional thumbnails.
    if include_thumbnails:
        for name in core_verdict.frames_analyzed:
            frame_path = frames_dir / name
            if not frame_path.is_file():
                continue
            try:
                files[f"thumbnails/{Path(name).stem}.jpg"] = _make_thumbnail(
                    frame_path, thumbnail_px
                )
            except Exception:
                # A thumbnail failure should not block the bundle.
                continue

    return files


def write_evidence_bundle(
    output_path: Path,
    *,
    verdict: EnhancedVerdict | Verdict,
    manifest_path: Path,
    frames_dir: Path,
    include_thumbnails: bool = False,
    redact_raw_outputs: bool = False,
    thumbnail_px: int = DEFAULT_THUMBNAIL_PX,
    extra_metadata: dict[str, Any] | None = None,
) -> Path:
    """Build the bundle and write it as a tar.gz to ``output_path``."""
    files = build_evidence_bundle(
        verdict=verdict,
        manifest_path=manifest_path,
        frames_dir=frames_dir,
        include_thumbnails=include_thumbnails,
        redact_raw_outputs=redact_raw_outputs,
        thumbnail_px=thumbnail_px,
        extra_metadata=extra_metadata,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output_path, "w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(info, io.BytesIO(data))
    return output_path


def _verdict_dump(
    verdict: EnhancedVerdict | Verdict, *, redact_raw_outputs: bool
) -> dict[str, Any]:
    dump = verdict.model_dump(mode="json")
    if not redact_raw_outputs:
        return dump

    core_dump = dump.get("core") if isinstance(verdict, EnhancedVerdict) else dump
    if isinstance(core_dump, dict):
        _redact_core_frame_analyses(core_dump)

    panel_dump = dump.get("panel")
    if isinstance(panel_dump, dict):
        for persona in panel_dump.get("per_persona", []):
            if isinstance(persona, dict):
                persona["raw_response"] = "[redacted]"

    return dump


def _redact_core_frame_analyses(core_dump: dict[str, Any]) -> None:
    for analysis in core_dump.get("frame_analyses", []):
        if isinstance(analysis, dict) and "raw_signals" in analysis:
            analysis["raw_signals"] = {"redacted": True}


def _redaction_manifest() -> dict[str, Any]:
    return {
        "redacted": True,
        "redacted_fields": [
            "verdict.core.frame_analyses[].raw_signals",
            "verdict.panel.per_persona[].raw_response",
            "panel/*.json.raw_response",
            "provider_outputs/*",
        ],
        "omitted_files": ["provider_outputs/*"],
        "note": (
            "Raw provider outputs and raw persona responses were omitted or "
            "replaced for external sharing. Frame hashes, verdict status, "
            "response-quality summaries, and panel findings remain."
        ),
    }
