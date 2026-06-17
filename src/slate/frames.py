"""Frame sampling — pick which frames in a sequence Slate analyzes.

Sampling modes (from :class:`slate.manifest.FrameSampling`):

* ``first_mid_last`` — three frames: index 0, len//2, len-1. Cheapest sample
  set; catches whole-shot failures (orientation, missing character, all-black)
  but misses mid-shot anomalies. Default.
* ``every_n`` — stride sampling. Use when you expect transient failures or
  want a denser audit.
* ``explicit`` — caller picks the exact indices. Useful for regression
  against known-bad-frame fixtures or for reproducing audit findings.
"""

from __future__ import annotations

from pathlib import Path

from slate.manifest import FrameSampling

#: File extensions Slate recognizes as render frames.
FRAME_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".tiff", ".bmp")


def list_frames(frames_dir: Path) -> list[Path]:
    """Return all frame files in ``frames_dir``, sorted by filename.

    Sorting is byte-wise on the filename — render pipelines that use
    zero-padded indices (``frame_0000.png``, ``frame_0001.png``, …) will sort
    in playback order. Pipelines that use non-padded indices will not, and
    callers should fix their naming rather than have Slate try to outsmart it.
    """
    if not frames_dir.is_dir():
        raise FileNotFoundError(f"frames directory not found: {frames_dir}")
    frames = sorted(
        p for p in frames_dir.iterdir() if p.is_file() and p.suffix.lower() in FRAME_EXTENSIONS
    )
    return frames


def sample_indices(total: int, sampling: FrameSampling) -> list[int]:
    """Return the 0-based indices Slate will analyze for a sequence of ``total`` frames."""
    if total <= 0:
        return []

    if sampling.mode == "first_mid_last":
        if total == 1:
            return [0]
        if total == 2:
            return [0, 1]
        return [0, total // 2, total - 1]

    if sampling.mode == "every_n":
        stride = max(1, sampling.every_n)
        idx = list(range(0, total, stride))
        # Always include the last frame so end-of-shot failures aren't missed.
        if idx[-1] != total - 1:
            idx.append(total - 1)
        return idx

    if sampling.mode == "explicit":
        return [i for i in sampling.explicit_indices if 0 <= i < total]

    raise ValueError(f"unknown sampling mode: {sampling.mode!r}")


def sample_frames(frames: list[Path], sampling: FrameSampling) -> list[Path]:
    """Pick frames from a sorted frame list according to the sampling mode."""
    return [frames[i] for i in sample_indices(len(frames), sampling)]
