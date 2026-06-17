"""Evidence bundle tests."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest
from PIL import Image

from slate.evidence import build_evidence_bundle, write_evidence_bundle
from slate.evidence.bundle import _make_thumbnail
from slate.manifest import Manifest
from slate.panel.fusion import fuse
from slate.panel.verdict import EnhancedVerdict, PersonaVerdict
from slate.verdict import FrameAnalysis, Verdict


@pytest.fixture
def manifest_path(tmp_path: Path, sample_manifest: Manifest) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(sample_manifest.model_dump_json(indent=2), "utf-8")
    return p


def _verdict_with_analyses(passing_core_verdict: Verdict) -> Verdict:
    """Add a couple of FrameAnalysis records so provider_outputs/ exercises."""
    return passing_core_verdict.model_copy(
        update={
            "frame_analyses": [
                FrameAnalysis(
                    frame="frame_0000.png",
                    provider="gemma",
                    model="gemma4:latest",
                    raw_signals={"character_visible": True},
                    quality_scores={"lighting_quality": 4.0},
                ),
                FrameAnalysis(
                    frame="frame_0000.png",
                    provider="nvidia-primary",
                    model="nvidia/nemotron-nano-12b-v2-vl",
                    raw_signals={"character_visible": True},
                    quality_scores={"lighting_quality": 4.0},
                ),
            ]
        }
    )


def test_build_evidence_bundle_for_core_only(
    passing_core_verdict: Verdict,
    manifest_path: Path,
    frames_dir: Path,
) -> None:
    verdict = _verdict_with_analyses(passing_core_verdict)
    files = build_evidence_bundle(
        verdict=verdict,
        manifest_path=manifest_path,
        frames_dir=frames_dir,
        include_thumbnails=False,
    )

    assert "verdict.json" in files
    assert "manifest.json" in files
    assert "environment.json" in files
    assert "frame_hashes.json" in files
    assert "provider_outputs/gemma.json" in files
    assert "provider_outputs/nvidia-primary.json" in files

    env = json.loads(files["environment.json"])
    assert "slate_version" in env


def test_build_evidence_bundle_for_panel_verdict(
    passing_core_verdict: Verdict,
    manifest_path: Path,
    frames_dir: Path,
) -> None:
    """When verdict is EnhancedVerdict, panel/<persona>.json entries appear."""
    core = _verdict_with_analyses(passing_core_verdict)
    personas = [
        PersonaVerdict(
            name=n, model="claude-sonnet-4-6", publish_ready=True, raw_response="ok"
        )
        for n in ("director", "color_grader", "animator", "audience")
    ]
    panel = fuse(personas, slate_version="0.1.0", duration_seconds=1.0)
    enhanced = EnhancedVerdict.from_core_and_panel(core, panel)
    files = build_evidence_bundle(
        verdict=enhanced,
        manifest_path=manifest_path,
        frames_dir=frames_dir,
        include_thumbnails=False,
    )

    for name in ("director", "color_grader", "animator", "audience"):
        assert f"panel/{name}.json" in files
    assert "response_quality.json" in files
    assert "panel/response_quality.json" in files


def test_redacted_bundle_omits_raw_provider_outputs_and_persona_text(
    passing_core_verdict: Verdict,
    manifest_path: Path,
    frames_dir: Path,
) -> None:
    core = _verdict_with_analyses(passing_core_verdict)
    personas = [
        PersonaVerdict(
            name=n,
            model="claude-sonnet-4-6",
            publish_ready=True,
            raw_response="raw model transcript",
        )
        for n in ("director", "color_grader", "animator", "audience")
    ]
    panel = fuse(personas, slate_version="0.1.0", duration_seconds=1.0)
    enhanced = EnhancedVerdict.from_core_and_panel(core, panel)

    files = build_evidence_bundle(
        verdict=enhanced,
        manifest_path=manifest_path,
        frames_dir=frames_dir,
        redact_raw_outputs=True,
    )

    assert "redaction.json" in files
    assert "provider_outputs/gemma.json" not in files
    assert "provider_outputs/nvidia-primary.json" not in files

    verdict_dump = json.loads(files["verdict.json"])
    assert (
        verdict_dump["panel"]["per_persona"][0]["raw_response"]
        == "[redacted]"
    )
    assert verdict_dump["core"]["frame_analyses"][0]["raw_signals"] == {
        "redacted": True
    }

    director_dump = json.loads(files["panel/director.json"])
    assert director_dump["raw_response"] == "[redacted]"


def test_write_evidence_bundle_round_trips(
    passing_core_verdict: Verdict,
    manifest_path: Path,
    frames_dir: Path,
    tmp_path: Path,
) -> None:
    """End-to-end: write a .tar.gz, then read it back and confirm contents."""
    verdict = _verdict_with_analyses(passing_core_verdict)
    bundle_path = tmp_path / "evidence.tar.gz"
    write_evidence_bundle(
        bundle_path,
        verdict=verdict,
        manifest_path=manifest_path,
        frames_dir=frames_dir,
        include_thumbnails=True,
    )
    assert bundle_path.is_file()
    assert bundle_path.stat().st_size > 0

    with tarfile.open(bundle_path, "r:gz") as tar:
        names = tar.getnames()
        assert "verdict.json" in names
        assert "manifest.json" in names
        assert "environment.json" in names
        assert "frame_hashes.json" in names
        # At least one thumbnail
        assert any(n.startswith("thumbnails/") for n in names)


def test_frame_hashes_use_sha256(
    passing_core_verdict: Verdict,
    manifest_path: Path,
    frames_dir: Path,
) -> None:
    verdict = passing_core_verdict.model_copy(
        update={"frames_analyzed": ["frame_0000.png"]}
    )
    files = build_evidence_bundle(
        verdict=verdict,
        manifest_path=manifest_path,
        frames_dir=frames_dir,
        include_thumbnails=False,
    )
    hashes = json.loads(files["frame_hashes.json"])
    assert "frame_0000.png" in hashes
    # SHA-256 hex digest is 64 characters
    assert len(hashes["frame_0000.png"]) == 64


# ---------------------------------------------------------------------------
# Thumbnail edge cases (bundle.py 91, 163, 168-170)
# ---------------------------------------------------------------------------


def test_make_thumbnail_converts_non_rgb_to_rgb(tmp_path: Path) -> None:
    """A non-RGB (grayscale 'L') source is converted to RGB before JPEG encode
    (bundle.py line 91)."""
    src = tmp_path / "gray.png"
    Image.new("L", (512, 512), 128).save(src, "PNG")
    data = _make_thumbnail(src, 256)
    assert data[:2] == b"\xff\xd8"  # JPEG SOI marker -> encode succeeded
    # Decoding the produced thumbnail yields an RGB image within the bound.
    from io import BytesIO

    out = Image.open(BytesIO(data))
    assert out.mode == "RGB"
    assert max(out.size) <= 256


def test_bundle_skips_thumbnail_for_missing_frame(
    passing_core_verdict: Verdict, manifest_path: Path, tmp_path: Path
) -> None:
    """A frame listed in the verdict but absent on disk is skipped in the
    thumbnail loop (bundle.py line 163) — and also absent from frame_hashes."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    # Only frame_0000 exists; frame_0005 is referenced but missing.
    Image.new("RGB", (16, 16), (255, 0, 0)).save(frames_dir / "frame_0000.png", "PNG")
    verdict = passing_core_verdict.model_copy(
        update={"frames_analyzed": ["frame_0000.png", "frame_0005.png"]}
    )
    files = build_evidence_bundle(
        verdict=verdict,
        manifest_path=manifest_path,
        frames_dir=frames_dir,
        include_thumbnails=True,
    )
    assert "thumbnails/frame_0000.jpg" in files
    assert "thumbnails/frame_0005.jpg" not in files
    hashes = json.loads(files["frame_hashes.json"])
    assert "frame_0005.png" not in hashes


def test_bundle_skips_thumbnail_when_generation_fails(
    passing_core_verdict: Verdict, manifest_path: Path, tmp_path: Path
) -> None:
    """A file that exists but is not a decodable image makes _make_thumbnail
    raise; the bundle swallows it and continues (bundle.py lines 168-170)."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    good = frames_dir / "frame_0000.png"
    Image.new("RGB", (16, 16), (0, 255, 0)).save(good, "PNG")
    # A bogus .png that PIL cannot open.
    (frames_dir / "frame_0001.png").write_bytes(b"not really a png")
    verdict = passing_core_verdict.model_copy(
        update={"frames_analyzed": ["frame_0000.png", "frame_0001.png"]}
    )
    files = build_evidence_bundle(
        verdict=verdict,
        manifest_path=manifest_path,
        frames_dir=frames_dir,
        include_thumbnails=True,
    )
    # Good frame produced a thumbnail; the corrupt one was skipped, not fatal.
    assert "thumbnails/frame_0000.jpg" in files
    assert "thumbnails/frame_0001.jpg" not in files
    # But its hash is still recorded (hashing raw bytes never fails).
    hashes = json.loads(files["frame_hashes.json"])
    assert "frame_0001.png" in hashes
