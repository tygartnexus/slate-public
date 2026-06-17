"""``slate verify`` CLI — the entry point exposed via the ``slate`` console script.

Exit codes:
    0  PASS — every configured signal passed for every analyzed frame.
    1  FAIL — at least one hard-fail signal triggered.
    2  INDETERMINATE — at least one provider was unreachable / returned bad
       output and no content failures were observed. The caller may want to
       retry rather than treat this as a publishing decision.
    3  Slate itself errored (bad manifest, missing frames directory, etc.)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from rich.console import Console
from rich.table import Table

from slate import __version__
from slate.engine import verify as engine_verify
from slate.evidence import write_evidence_bundle
from slate.manifest import Manifest
from slate.panel import (
    DEFAULT_PANEL_MODEL,
    ClaudeVisionClient,
    EnhancedStatus,
    EnhancedVerdict,
    run_panel,
)
from slate.panel.local_ollama_client import LocalOllamaVisionClient
from slate.panel.personas.base import VisionPanelClient
from slate.providers import GemmaProvider, NvidiaProvider, VLMProvider
from slate.providers.nvidia import DEFAULT_CROSSCHECK_MODEL, DEFAULT_PRIMARY_MODEL
from slate.verdict import Verdict, VerdictStatus

app = typer.Typer(
    name="slate",
    help="Don't ship broken AI animation. Multi-VLM verdict for rendered frames.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()
ProviderChoice = Literal["auto", "gemma", "nvidia", "both"]


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"slate {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print Slate version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Shared root options."""


@app.command()
def verify(
    frames: Annotated[
        Path,
        typer.Option(
            "--frames",
            "-f",
            help="Directory containing the rendered frame sequence.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ],
    manifest: Annotated[
        Path,
        typer.Option(
            "--manifest",
            "-m",
            help="Slate manifest JSON describing what the shot should contain.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write the verdict JSON here. Defaults to stdout.",
        ),
    ] = None,
    bundle: Annotated[
        Path | None,
        typer.Option("--bundle", help="Also write an evidence bundle to this .tar.gz."),
    ] = None,
    include_thumbnails: Annotated[
        bool,
        typer.Option(
            "--include-thumbnails",
            help="Include opt-in 256-px JPEG thumbnails in the evidence bundle.",
        ),
    ] = False,
    redact_raw_outputs: Annotated[
        bool,
        typer.Option(
            "--redact-raw-outputs",
            help="Omit raw provider outputs and redact raw persona text in the bundle.",
        ),
    ] = False,
    provider: Annotated[
        ProviderChoice,
        typer.Option(
            "--provider",
            "-p",
            help="Which VLM backend(s) to use. 'auto' uses both if NVIDIA_API_KEY is set.",
        ),
    ] = "auto",
    nvidia_primary_model: Annotated[
        str,
        typer.Option(
            "--nvidia-primary-model",
            help="NVIDIA primary VLM model id.",
        ),
    ] = DEFAULT_PRIMARY_MODEL,
    nvidia_crosscheck_model: Annotated[
        str,
        typer.Option(
            "--nvidia-crosscheck-model",
            help="NVIDIA cross-check VLM model id (set to '' to disable).",
        ),
    ] = DEFAULT_CROSSCHECK_MODEL,
    panel: Annotated[
        bool,
        typer.Option("--panel", help="Run the four-persona Panel after Core passes."),
    ] = False,
    panel_model: Annotated[
        str,
        typer.Option("--panel-model", help="Model id for Panel personas."),
    ] = DEFAULT_PANEL_MODEL,
    panel_provider: Annotated[
        Literal["anthropic", "local"],
        typer.Option(
            "--panel-provider",
            help="Panel provider: anthropic uses ANTHROPIC_API_KEY; local uses Ollama.",
        ),
    ] = "anthropic",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress the human-readable summary on stderr."),
    ] = False,
) -> None:
    """Run the verdict engine against ``frames`` using ``manifest``."""
    try:
        loaded_manifest = Manifest.from_file(manifest)
    except Exception as exc:
        console.print(f"[red]manifest invalid:[/red] {exc}")
        raise typer.Exit(3) from exc

    providers = _build_providers(provider, nvidia_primary_model, nvidia_crosscheck_model)
    if not providers:
        console.print(
            "[red]no providers configured[/red] — set NVIDIA_API_KEY or run "
            "Ollama locally with gemma4:latest"
        )
        raise typer.Exit(3)

    core_verdict = engine_verify(
        manifest=loaded_manifest, frames_dir=frames, providers=providers
    )
    verdict: Verdict | EnhancedVerdict = core_verdict

    if panel:
        client: VisionPanelClient
        if panel_provider == "local":
            local_model = (
                os.environ.get("GEMMA_MODEL", "gemma4:latest")
                if panel_model == DEFAULT_PANEL_MODEL
                else panel_model
            )
            client = LocalOllamaVisionClient(model=local_model)
        else:
            client = ClaudeVisionClient(model=panel_model)
        verdict = run_panel(
            core_verdict=core_verdict,
            manifest=loaded_manifest,
            frames_dir=frames,
            client=client,
        )

    if output:
        output.write_text(verdict.model_dump_json(indent=2), "utf-8")
    else:
        sys.stdout.write(verdict.model_dump_json(indent=2) + "\n")

    if bundle:
        try:
            write_evidence_bundle(
                bundle,
                verdict=verdict,
                manifest_path=manifest,
                frames_dir=frames,
                include_thumbnails=include_thumbnails,
                redact_raw_outputs=redact_raw_outputs,
            )
            if not quiet:
                console.print(f"[green]evidence bundle:[/green] {bundle}")
        except Exception as exc:
            console.print(f"[yellow]bundle write failed:[/yellow] {exc}")

    if not quiet:
        _print_summary(verdict)

    if _is_pass(verdict):
        raise typer.Exit(0)
    if _is_indeterminate(verdict):
        raise typer.Exit(2)
    raise typer.Exit(1)


def _build_providers(
    selection: ProviderChoice,
    nvidia_primary_model: str,
    nvidia_crosscheck_model: str,
) -> list[VLMProvider]:
    has_nvidia_key = bool(os.environ.get("NVIDIA_API_KEY"))
    if selection == "auto":
        selection = "both" if has_nvidia_key else "gemma"

    providers: list[VLMProvider] = []
    if selection in {"gemma", "both"}:
        providers.append(GemmaProvider())
    if selection in {"nvidia", "both"}:
        if not has_nvidia_key:
            console.print(
                "[yellow]warning:[/yellow] --provider includes nvidia but "
                "NVIDIA_API_KEY is not set; skipping NVIDIA lane"
            )
        else:
            providers.append(
                NvidiaProvider(label="nvidia-primary", model=nvidia_primary_model)
            )
            if nvidia_crosscheck_model:
                providers.append(
                    NvidiaProvider(
                        label="nvidia-crosscheck", model=nvidia_crosscheck_model
                    )
                )
    return providers


def _print_summary(verdict: Verdict | EnhancedVerdict) -> None:
    core = verdict.core if isinstance(verdict, EnhancedVerdict) else verdict
    status = verdict.final_status if isinstance(verdict, EnhancedVerdict) else verdict.status
    color = _status_color(status)
    panel_part = ""
    if isinstance(verdict, EnhancedVerdict) and verdict.panel is not None:
        panel_part = f" panel={_panel_summary_label(verdict)}"
    console.print(
        f"\n[bold {color}]{status.value}[/bold {color}] — "
        f"shot={core.shot_id} duration={core.duration_seconds}s "
        f"providers={','.join(core.providers_consulted)} "
        f"frames={len(core.frames_analyzed)} "
        f"failures={len(core.failures)}"
        f"{panel_part}",
        soft_wrap=True,
    )
    if core.failures:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Frame")
        table.add_column("Provider")
        table.add_column("Signal", style="red")
        table.add_column("Value")
        for f in core.failures[:20]:
            table.add_row(f.frame, f.provider, f.signal, str(f.value))
        console.print(table)
        if len(core.failures) > 20:
            console.print(f"...and {len(core.failures) - 20} more failures")


def _status_color(status: VerdictStatus | EnhancedStatus) -> str:
    return {
        VerdictStatus.PASS: "green",
        VerdictStatus.FAIL: "red",
        VerdictStatus.INDETERMINATE: "yellow",
        EnhancedStatus.PASS: "green",
        EnhancedStatus.FAIL: "red",
        EnhancedStatus.PANEL_BLOCKED: "magenta",
        EnhancedStatus.INDETERMINATE: "yellow",
    }[status]


def _panel_summary_label(verdict: EnhancedVerdict) -> str:
    if verdict.panel is None:
        return "SKIPPED"
    if any(persona.error for persona in verdict.panel.per_persona):
        return "INDETERMINATE"
    return "PASS" if verdict.panel.publish_ready else "BLOCK"


def _is_pass(verdict: Verdict | EnhancedVerdict) -> bool:
    if isinstance(verdict, EnhancedVerdict):
        return verdict.final_status == EnhancedStatus.PASS
    return verdict.status == VerdictStatus.PASS


def _is_indeterminate(verdict: Verdict | EnhancedVerdict) -> bool:
    if isinstance(verdict, EnhancedVerdict):
        return verdict.final_status == EnhancedStatus.INDETERMINATE
    return verdict.status == VerdictStatus.INDETERMINATE


@app.command()
def bundle(
    verdict_path: Annotated[
        Path,
        typer.Option("--verdict", "-V", exists=True, file_okay=True, dir_okay=False),
    ],
    manifest_path: Annotated[
        Path,
        typer.Option("--manifest", "-m", exists=True, file_okay=True, dir_okay=False),
    ],
    frames: Annotated[
        Path,
        typer.Option("--frames", "-f", exists=True, file_okay=False, dir_okay=True),
    ],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("evidence.tar.gz"),
    include_thumbnails: bool = typer.Option(
        False,
        "--include-thumbnails",
        help="Include opt-in 256-px JPEG thumbnails in the evidence bundle.",
    ),
    redact_raw_outputs: bool = typer.Option(
        False,
        "--redact-raw-outputs",
        help="Omit raw provider outputs and redact raw persona text in the bundle.",
    ),
) -> None:
    """Build an evidence bundle from a previously-written verdict JSON."""
    try:
        raw = json.loads(verdict_path.read_text("utf-8"))
    except Exception as exc:
        console.print(f"[red]verdict file unreadable:[/red] {exc}")
        raise typer.Exit(3) from exc

    try:
        verdict = (
            EnhancedVerdict.model_validate(raw)
            if "final_status" in raw
            else _core_verdict_from_dict(raw)
        )
    except Exception as exc:
        console.print(f"[red]verdict shape unrecognized:[/red] {exc}")
        raise typer.Exit(3) from exc

    written = write_evidence_bundle(
        output,
        verdict=verdict,
        manifest_path=manifest_path,
        frames_dir=frames,
        include_thumbnails=include_thumbnails,
        redact_raw_outputs=redact_raw_outputs,
    )
    console.print(f"[green]wrote[/green] {written}")


def _core_verdict_from_dict(raw: dict[str, Any]) -> Verdict:
    return Verdict.model_validate(raw)


if __name__ == "__main__":  # pragma: no cover - console-script entrypoint
    app()
