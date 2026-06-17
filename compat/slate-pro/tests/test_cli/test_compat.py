"""Compatibility tests for the deprecated slate-pro wrapper."""

from __future__ import annotations

from slate.cli import app as slate_app
from slate.evidence import build_evidence_bundle
from slate.panel import DEFAULT_PANEL_MODEL
from slate.panel.verdict import EnhancedVerdict
from typer.testing import CliRunner

import slate_pro
import slate_pro.cli as compat_cli
from slate_pro.evidence import build_evidence_bundle as compat_build_evidence_bundle
from slate_pro.panel import DEFAULT_PRO_MODEL
from slate_pro.panel.verdict import EnhancedVerdict as CompatEnhancedVerdict

runner = CliRunner()


def test_console_script_delegates_to_slate_cli() -> None:
    assert compat_cli.app is slate_app
    result = runner.invoke(compat_cli.app, ["--version"])
    assert result.exit_code == 0
    assert "slate " in result.stdout


def test_import_shims_delegate_to_slate() -> None:
    assert DEFAULT_PRO_MODEL == DEFAULT_PANEL_MODEL
    assert CompatEnhancedVerdict is EnhancedVerdict
    assert compat_build_evidence_bundle is build_evidence_bundle
    assert slate_pro.__version__ == "0.1.0"
