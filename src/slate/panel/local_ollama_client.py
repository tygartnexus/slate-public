"""Local Ollama-backed client for Slate Panel personas.

This client implements the same tiny interface as ``ClaudeVisionClient``:
``model`` plus ``analyze(prompt, frames)`` returning ``ClaudeResponse``. That
lets the existing persona code run unchanged while swapping the Panel provider.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

from slate import config
from slate.panel.claude_client import ClaudeResponse
from slate.providers.base import encode_image_b64


class LocalOllamaVisionClient:
    """Panel-compatible local vision client using Ollama's ``/api/generate``."""

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

    def analyze(self, prompt: str, frames: list[Path]) -> ClaudeResponse:
        try:
            images = [
                encode_image_b64(frame, max_dim=self.max_image_dim)
                for frame in frames
            ]
        except OSError as exc:
            return ClaudeResponse(text="", model=self.model, error=f"read frame: {exc}")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": images,
            "stream": False,
            "options": {
                "num_predict": 2000,
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
            return ClaudeResponse(text="", model=self.model, error=f"ollama: {exc}")
        except ValueError as exc:
            return ClaudeResponse(
                text="", model=self.model, error=f"ollama: bad json: {exc}"
            )

        return ClaudeResponse(text=str(data.get("response") or "").strip(), model=self.model)
