"""Frame discovery + sampling tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from slate.frames import list_frames, sample_frames, sample_indices
from slate.manifest import FrameSampling


def test_list_frames_returns_sorted(frames_dir: Path) -> None:
    frames = list_frames(frames_dir)
    assert [f.name for f in frames] == [f"frame_{i:04d}.png" for i in range(10)]


def test_list_frames_ignores_non_image(frames_dir: Path) -> None:
    (frames_dir / "notes.txt").write_text("ignore me", "utf-8")
    frames = list_frames(frames_dir)
    assert all(f.suffix.lower() != ".txt" for f in frames)


def test_list_frames_raises_for_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list_frames(tmp_path / "nope")


def test_first_mid_last_default() -> None:
    assert sample_indices(10, FrameSampling()) == [0, 5, 9]


def test_first_mid_last_handles_short_sequences() -> None:
    assert sample_indices(0, FrameSampling()) == []
    assert sample_indices(1, FrameSampling()) == [0]
    assert sample_indices(2, FrameSampling()) == [0, 1]


def test_every_n_includes_last_frame() -> None:
    s = FrameSampling(mode="every_n", every_n=4)
    assert sample_indices(10, s) == [0, 4, 8, 9]


def test_explicit_skips_out_of_range_indices() -> None:
    s = FrameSampling(mode="explicit", explicit_indices=[-1, 0, 5, 50])
    assert sample_indices(10, s) == [0, 5]


def test_sample_frames_returns_path_objects(frames_dir: Path) -> None:
    frames = list_frames(frames_dir)
    sampled = sample_frames(frames, FrameSampling())
    assert [f.name for f in sampled] == [
        "frame_0000.png",
        "frame_0005.png",
        "frame_0009.png",
    ]


def test_unknown_sampling_mode_raises() -> None:
    # ``mode`` is a Literal at the schema boundary; bypass validation to reach
    # the engine's defensive guard against an unrecognized mode.
    bogus = FrameSampling.model_construct(mode="bogus", every_n=60, explicit_indices=[])
    with pytest.raises(ValueError, match="unknown sampling mode"):
        sample_indices(5, bogus)
