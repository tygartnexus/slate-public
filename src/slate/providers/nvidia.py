"""NVIDIA NIM provider — OpenAI-compatible chat completions API.

Customer brings their own ``NVIDIA_API_KEY`` (Slate never proxies it).
Default endpoint: ``https://integrate.api.nvidia.com/v1``.

Slate's standard configuration uses two NVIDIA models for cross-check:

* Primary: ``nvidia/nemotron-nano-12b-v2-vl``
* Cross-check: ``meta/llama-3.2-90b-vision-instruct``

Construct two ``NvidiaProvider`` instances with distinct labels (e.g.
``"nvidia-primary"`` and ``"nvidia-crosscheck"``) to run both lanes.
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

DEFAULT_PRIMARY_MODEL = "nvidia/nemotron-nano-12b-v2-vl"
DEFAULT_CROSSCHECK_MODEL = "meta/llama-3.2-90b-vision-instruct"


class NvidiaProvider:
    """VLMProvider talking to NVIDIA's OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        *,
        label: str = "nvidia",
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 700,
        timeout_seconds: int | None = None,
        max_image_dim: int | None = None,
    ) -> None:
        self.label = label
        self.model = model or DEFAULT_PRIMARY_MODEL
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY") or ""
        self.base_url = (
            base_url
            or os.environ.get("NVIDIA_API_BASE_URL")
            or "https://integrate.api.nvidia.com/v1"
        ).rstrip("/")
        self.max_tokens = max_tokens
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else config.provider_timeout()
        )
        self.max_image_dim = (
            max_image_dim if max_image_dim is not None else config.max_image_dim()
        )

    def analyze_frame(self, frame_path: Path, manifest: Manifest) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(
                self.label,
                self.model,
                {},
                error="nvidia: NVIDIA_API_KEY is not configured",
            )

        try:
            b64 = encode_image_b64(frame_path, max_dim=self.max_image_dim)
        except OSError as exc:
            return ProviderResult(self.label, self.model, {}, error=f"read {frame_path}: {exc}")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_frame_analysis_prompt(manifest),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": self.max_tokens,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as exc:
            detail = exc.response.text[:400] if exc.response is not None else ""
            return ProviderResult(
                self.label,
                self.model,
                {},
                error=f"nvidia {self.model}: HTTP {exc.response.status_code if exc.response else '?'}: {detail}",
            )
        except requests.RequestException as exc:
            return ProviderResult(self.label, self.model, {}, error=f"nvidia {self.model}: {exc}")
        except ValueError as exc:
            return ProviderResult(
                self.label, self.model, {}, error=f"nvidia {self.model}: bad json: {exc}"
            )

        choices = data.get("choices") or []
        if not choices:
            return ProviderResult(
                self.label, self.model, {}, error=f"nvidia {self.model}: no choices returned"
            )
        message = choices[0].get("message", {}) or {}
        raw = message.get("content", "")
        if isinstance(raw, list):
            raw = " ".join(str(part.get("text", part)) for part in raw)
        parsed = parse_strict_json(str(raw), self.model)
        if "error" in parsed:
            return ProviderResult(self.label, self.model, parsed, error=str(parsed["error"]))
        return ProviderResult(self.label, self.model, parsed)
