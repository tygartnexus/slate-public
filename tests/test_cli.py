"""CLI tests for ``slate verify``.

The engine is always mocked (``slate.cli.engine_verify``) so no provider, model,
network call, or API key is ever exercised here — these tests only cover
argument handling, provider selection, output routing, the human-readable
summary, and exit-code mapping. Frames dir + manifest file are created under
``tmp_path`` so Typer's ``exists=True`` path validation is satisfied with real
files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from typer.testing import CliRunner

import slate.cli as cli
from slate import __version__
from slate.panel.verdict import EnhancedStatus, EnhancedVerdict, PanelVerdict, PersonaVerdict
from slate.verdict import SignalFailure, Verdict, VerdictStatus

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def frames_dir(tmp_path: Path) -> Path:
    d = tmp_path / "frames"
    d.mkdir()
    for i in range(3):
        Image.new("RGB", (4, 4), (i, i, i)).save(d / f"frame_{i:04d}.png", "PNG")
    return d


@pytest.fixture
def manifest_file(tmp_path: Path) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"shot_id": "village_walk_001"}), "utf-8")
    return p


def _make_verdict(
    status: VerdictStatus,
    *,
    failures: list[SignalFailure] | None = None,
    providers: list[str] | None = None,
) -> Verdict:
    return Verdict(
        status=status,
        shot_id="village_walk_001",
        slate_version=__version__,
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        duration_seconds=1.0,
        providers_consulted=providers or ["gemma"],
        frames_analyzed=["frame_0000.png", "frame_0001.png", "frame_0002.png"],
        failures=failures or [],
    )


def _patch_engine(monkeypatch: pytest.MonkeyPatch, verdict: Verdict) -> dict[str, Any]:
    """Patch the engine entrypoint to return ``verdict``; capture its kwargs."""
    captured: dict[str, Any] = {}

    def fake_verify(**kwargs: Any) -> Verdict:
        captured.update(kwargs)
        return verdict

    monkeypatch.setattr(cli, "engine_verify", fake_verify)
    return captured


def _fail(signal: str, frame: str = "frame_0000.png") -> SignalFailure:
    return SignalFailure(
        signal=signal, value=False, frame=frame, provider="gemma", model="gemma4:latest"
    )


# ---------------------------------------------------------------------------
# Root / version
# ---------------------------------------------------------------------------


def test_version_flag() -> None:
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert f"slate {__version__}" in result.stdout


def test_no_args_shows_help() -> None:
    result = runner.invoke(cli.app, [])
    # no_args_is_help -> Typer exits 0 (or 2) and prints usage; never crashes.
    assert result.exit_code in (0, 2)
    assert "verify" in result.stdout


# ---------------------------------------------------------------------------
# Exit-code mapping
# ---------------------------------------------------------------------------


def test_verify_pass_exits_zero(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    _patch_engine(monkeypatch, _make_verdict(VerdictStatus.PASS))
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "gemma"],
    )
    assert result.exit_code == 0
    assert '"status": "PASS"' in result.stdout


def test_verify_fail_exits_one(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    verdict = _make_verdict(VerdictStatus.FAIL, failures=[_fail("character_visible")])
    _patch_engine(monkeypatch, verdict)
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "gemma"],
    )
    assert result.exit_code == 1
    assert '"status": "FAIL"' in result.stdout


def test_verify_indeterminate_exits_two(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    _patch_engine(monkeypatch, _make_verdict(VerdictStatus.INDETERMINATE))
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "gemma"],
    )
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_invalid_manifest_exits_three(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", "utf-8")

    def boom(**kwargs: Any) -> Verdict:
        raise AssertionError("engine must not run on an invalid manifest")

    monkeypatch.setattr(cli, "engine_verify", boom)
    result = runner.invoke(
        cli.app, ["verify", "-f", str(frames_dir), "-m", str(bad)]
    )
    assert result.exit_code == 3
    assert "manifest invalid" in result.stdout


def test_no_providers_exits_three(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    # provider=nvidia but no key -> nvidia lane skipped -> empty provider list.
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    def boom(**kwargs: Any) -> Verdict:
        raise AssertionError("engine must not run with zero providers")

    monkeypatch.setattr(cli, "engine_verify", boom)
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "nvidia"],
    )
    assert result.exit_code == 3
    assert "no providers configured" in result.stdout


def test_missing_frames_dir_is_usage_error(
    monkeypatch: pytest.MonkeyPatch, manifest_file: Path, tmp_path: Path
) -> None:
    _patch_engine(monkeypatch, _make_verdict(VerdictStatus.PASS))
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(tmp_path / "missing"), "-m", str(manifest_file)],
    )
    # Typer rejects a non-existent --frames before the command body runs.
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Output routing + summary
# ---------------------------------------------------------------------------


def test_output_written_to_file(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path, tmp_path: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    _patch_engine(monkeypatch, _make_verdict(VerdictStatus.PASS))
    out = tmp_path / "verdict.json"
    result = runner.invoke(
        cli.app,
        [
            "verify",
            "-f",
            str(frames_dir),
            "-m",
            str(manifest_file),
            "-p",
            "gemma",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0
    assert out.exists()
    written = json.loads(out.read_text("utf-8"))
    assert written["status"] == "PASS"
    # When writing to a file the JSON is not echoed to stdout.
    assert '"status": "PASS"' not in result.stdout


def test_quiet_suppresses_summary(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    _patch_engine(monkeypatch, _make_verdict(VerdictStatus.PASS))
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "gemma", "-q"],
    )
    assert result.exit_code == 0
    # The summary line prints the status word in a styled banner; quiet hides it.
    assert "shot=" not in result.stdout


def test_summary_renders_failure_table(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    verdict = _make_verdict(
        VerdictStatus.FAIL,
        failures=[_fail("character_visible"), _fail("scale_plausible")],
    )
    _patch_engine(monkeypatch, verdict)
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "gemma"],
    )
    assert result.exit_code == 1
    assert "shot=" in result.stdout
    assert "character_visible" in result.stdout
    assert "Signal" in result.stdout  # table header


def test_summary_truncates_many_failures(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    failures = [_fail("character_visible", frame=f"frame_{i:04d}.png") for i in range(25)]
    _patch_engine(monkeypatch, _make_verdict(VerdictStatus.FAIL, failures=failures))
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "gemma"],
    )
    assert result.exit_code == 1
    # 25 failures, table caps at 20 -> "...and 5 more failures".
    assert "5 more failures" in result.stdout


# ---------------------------------------------------------------------------
# Provider selection (_build_providers)
# ---------------------------------------------------------------------------


def test_build_providers_auto_without_key_is_gemma_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    providers = cli._build_providers("auto", "primary-model", "crosscheck-model")
    assert [p.label for p in providers] == ["gemma"]


def test_build_providers_auto_with_key_is_both(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "key")
    providers = cli._build_providers("auto", "primary-model", "crosscheck-model")
    labels = [p.label for p in providers]
    assert labels == ["gemma", "nvidia-primary", "nvidia-crosscheck"]
    # The primary/crosscheck models are threaded through.
    nvidia = [p for p in providers if p.label.startswith("nvidia")]
    assert nvidia[0].model == "primary-model"
    assert nvidia[1].model == "crosscheck-model"


def test_build_providers_nvidia_without_key_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    providers = cli._build_providers("nvidia", "primary-model", "crosscheck-model")
    assert providers == []


def test_build_providers_nvidia_crosscheck_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "key")
    providers = cli._build_providers("nvidia", "primary-model", "")
    # Empty crosscheck model -> only the primary NVIDIA lane is built.
    assert [p.label for p in providers] == ["nvidia-primary"]


def test_build_providers_both_warns_when_key_missing(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    """provider=both without a key keeps gemma and warns about the skipped lane."""
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    _patch_engine(monkeypatch, _make_verdict(VerdictStatus.PASS))
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "both", "-q"],
    )
    assert result.exit_code == 0
    assert "NVIDIA_API_KEY is not set" in result.stdout


def test_verify_passes_loaded_manifest_and_frames_to_engine(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    captured = _patch_engine(monkeypatch, _make_verdict(VerdictStatus.PASS))
    result = runner.invoke(
        cli.app,
        ["verify", "-f", str(frames_dir), "-m", str(manifest_file), "-p", "gemma"],
    )
    assert result.exit_code == 0
    assert captured["manifest"].shot_id == "village_walk_001"
    assert captured["frames_dir"] == frames_dir.resolve()
    assert [p.label for p in captured["providers"]] == ["gemma"]


def test_verify_panel_runs_through_unified_slate_cli(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    core = _make_verdict(VerdictStatus.PASS)
    _patch_engine(monkeypatch, core)
    captured: dict[str, Any] = {}

    def fake_run_panel(**kwargs: Any) -> EnhancedVerdict:
        captured.update(kwargs)
        panel = PanelVerdict(publish_ready=True, summary="panel passed")
        return EnhancedVerdict.from_core_and_panel(kwargs["core_verdict"], panel)

    monkeypatch.setattr(cli, "run_panel", fake_run_panel)
    result = runner.invoke(
        cli.app,
        [
            "verify",
            "-f",
            str(frames_dir),
            "-m",
            str(manifest_file),
            "-p",
            "gemma",
            "--panel",
            "--panel-provider",
            "local",
            "--panel-model",
            "gemma4:latest",
        ],
    )

    assert result.exit_code == 0
    assert '"final_status": "PASS"' in result.stdout
    assert "panel=PASS" in result.stdout
    assert captured["core_verdict"] is core
    assert captured["manifest"].shot_id == "village_walk_001"
    assert captured["frames_dir"] == frames_dir.resolve()
    assert captured["client"].model == "gemma4:latest"


def test_verify_panel_indeterminate_exits_two_and_labels_panel(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    core = _make_verdict(VerdictStatus.PASS)
    _patch_engine(monkeypatch, core)

    def fake_run_panel(**kwargs: Any) -> EnhancedVerdict:
        panel = PanelVerdict(
            publish_ready=True,
            per_persona=[
                PersonaVerdict(
                    name="director",
                    model="local",
                    publish_ready=False,
                    error="invalid response_quality",
                )
            ],
        )
        return EnhancedVerdict.from_core_and_panel(kwargs["core_verdict"], panel)

    monkeypatch.setattr(cli, "run_panel", fake_run_panel)
    result = runner.invoke(
        cli.app,
        [
            "verify",
            "-f",
            str(frames_dir),
            "-m",
            str(manifest_file),
            "-p",
            "gemma",
            "--panel",
            "--panel-provider",
            "local",
        ],
    )

    assert result.exit_code == 2
    assert '"final_status": "INDETERMINATE"' in result.stdout
    assert "panel=INDETERMINATE" in result.stdout
    assert EnhancedStatus.INDETERMINATE.value in result.stdout


def test_verify_bundle_writes_evidence_bundle(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path, tmp_path: Path
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    verdict = _make_verdict(VerdictStatus.PASS)
    _patch_engine(monkeypatch, verdict)
    bundle_path = tmp_path / "evidence.tar.gz"
    captured: dict[str, Any] = {}

    def fake_write_evidence_bundle(output_path: Path, **kwargs: Any) -> Path:
        captured.update({"output_path": output_path, **kwargs})
        return output_path

    monkeypatch.setattr(cli, "write_evidence_bundle", fake_write_evidence_bundle)
    result = runner.invoke(
        cli.app,
        [
            "verify",
            "-f",
            str(frames_dir),
            "-m",
            str(manifest_file),
            "-p",
            "gemma",
            "--bundle",
            str(bundle_path),
            "--redact-raw-outputs",
            "-q",
        ],
    )

    assert result.exit_code == 0
    assert captured["output_path"] == bundle_path
    assert captured["verdict"] is verdict
    assert captured["manifest_path"] == manifest_file.resolve()
    assert captured["frames_dir"] == frames_dir.resolve()
    assert captured["redact_raw_outputs"] is True


def test_bundle_command_builds_bundle_from_core_verdict_json(
    monkeypatch: pytest.MonkeyPatch, frames_dir: Path, manifest_file: Path, tmp_path: Path
) -> None:
    verdict_path = tmp_path / "verdict.json"
    verdict_path.write_text(_make_verdict(VerdictStatus.PASS).model_dump_json(), "utf-8")
    bundle_path = tmp_path / "from-verdict.tar.gz"
    captured: dict[str, Any] = {}

    def fake_write_evidence_bundle(output_path: Path, **kwargs: Any) -> Path:
        captured.update({"output_path": output_path, **kwargs})
        return output_path

    monkeypatch.setattr(cli, "write_evidence_bundle", fake_write_evidence_bundle)
    result = runner.invoke(
        cli.app,
        [
            "bundle",
            "-V",
            str(verdict_path),
            "-m",
            str(manifest_file),
            "-f",
            str(frames_dir),
            "-o",
            str(bundle_path),
            "--include-thumbnails",
        ],
    )

    assert result.exit_code == 0
    assert captured["output_path"] == bundle_path
    assert isinstance(captured["verdict"], Verdict)
    assert captured["manifest_path"] == manifest_file
    assert captured["frames_dir"] == frames_dir
    assert captured["include_thumbnails"] is True
