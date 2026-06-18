"""Validate a live-provider certification verdict."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verdict", type=Path, required=True)
    parser.add_argument("--require-provider-prefix", default="")
    parser.add_argument("--require-panel", action="store_true")
    args = parser.parse_args()

    verdict = json.loads(args.verdict.read_text("utf-8"))
    failures = _all_failures(verdict)
    providers = verdict.get("providers_consulted") or verdict.get("core", {}).get(
        "providers_consulted", []
    )

    issues: list[str] = []
    if _status(verdict) == "INDETERMINATE":
        issues.append("verdict is INDETERMINATE")
    if any(failure.get("signal") == "__provider_error__" for failure in failures):
        issues.append("provider error failure was present")
    if any(
        failure.get("signal") == "__response_quality_missing__"
        for failure in failures
    ):
        issues.append("response_quality_missing failure was present")
    if not _has_response_quality(verdict):
        issues.append("top-level response_quality is missing")
    if args.require_provider_prefix and not any(
        str(provider).startswith(args.require_provider_prefix) for provider in providers
    ):
        issues.append(
            f"provider prefix {args.require_provider_prefix!r} not found in {providers!r}"
        )
    if args.require_panel and not verdict.get("panel"):
        issues.append("Panel result is required but missing")

    if issues:
        raise SystemExit("certification verdict failed: " + "; ".join(issues))

    print(
        json.dumps(
            {
                "status": _status(verdict),
                "providers_consulted": providers,
                "failure_count": len(failures),
                "has_panel": bool(verdict.get("panel")),
            },
            indent=2,
        )
    )


def _status(verdict: dict[str, Any]) -> str:
    return str(verdict.get("final_status") or verdict.get("status") or "UNKNOWN")


def _all_failures(verdict: dict[str, Any]) -> list[dict[str, Any]]:
    core = verdict.get("core") if isinstance(verdict.get("core"), dict) else verdict
    failures = core.get("failures", []) if isinstance(core, dict) else []
    return [failure for failure in failures if isinstance(failure, dict)]


def _has_response_quality(verdict: dict[str, Any]) -> bool:
    if isinstance(verdict.get("response_quality"), dict):
        return True
    core = verdict.get("core")
    return isinstance(core, dict) and isinstance(core.get("response_quality"), dict)


if __name__ == "__main__":
    main()
