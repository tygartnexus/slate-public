"""Local Gemma provider via Ollama's HTTP API.

Default endpoint: ``http://localhost:11434``. Default model: ``gemma4:latest``.
Override via constructor args or environment (``OLLAMA_URL``, ``GEMMA_MODEL``).
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

from slate import config
from slate.manifest import Manifest
from slate.prompts import build_frame_analysis_prompt
from slate.providers.base import (
    ProviderResult,
    encode_image_b64,
    parse_strict_json,
)


class GemmaProvider:
    """VLMProvider talking to a local Ollama daemon."""

    label = "gemma"

    def __init__(
        self,
        *,
        url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        max_image_dim: int | None = None,
    ) -> None:
        self.url = (url or os.environ.get("OLLAMA_URL") or "http://localhost:11434").rstrip("/")
        self.model = model or os.environ.get("GEMMA_MODEL") or "gemma4:latest"
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else config.provider_timeout()
        )
        self.max_image_dim = (
            max_image_dim if max_image_dim is not None else config.max_image_dim()
        )

    def analyze_frame(self, frame_path: Path, manifest: Manifest) -> ProviderResult:
        try:
            b64 = encode_image_b64(frame_path, max_dim=self.max_image_dim)
        except OSError as exc:
            return ProviderResult(self.label, self.model, {}, error=f"read {frame_path}: {exc}")

        payload = {
            "model": self.model,
            "prompt": build_frame_analysis_prompt(manifest),
            "images": [b64],
            "stream": False,
            "options": {
                "num_predict": _num_predict(),
                "temperature": 0.0,
            },
        }

        try:
            resp = requests.post(
                f"{self.url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            return ProviderResult(self.label, self.model, {}, error=f"ollama: {exc}")
        except ValueError as exc:
            return ProviderResult(self.label, self.model, {}, error=f"ollama: bad json: {exc}")

        raw = (data.get("response") or "").strip()
        parsed = parse_strict_json(raw, self.label)
        if "error" in parsed:
            return ProviderResult(self.label, self.model, parsed, error=str(parsed["error"]))
        return ProviderResult(self.label, self.model, parsed)

    def warm(self) -> bool:
        """Preload the model into memory.

        A cold Ollama model load can take ~30s; doing it once up front means the
        per-frame ``analyze_frame`` calls pay only inference cost (~1-3s on a
        downscaled frame). Returns True if the daemon was reachable.
        """
        try:
            resp = requests.post(
                f"{self.url}/api/generate",
                json={"model": self.model, "prompt": "ok", "stream": False},
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            return True
        except requests.RequestException:
            return False


def _num_predict() -> int:
    raw = os.environ.get("GEMMA_NUM_PREDICT")
    if raw:
        try:
            value = int(raw)
        except ValueError:
            return 2048
        return max(256, value)
    return 2048
