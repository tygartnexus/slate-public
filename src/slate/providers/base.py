"""VLMProvider protocol — the interface every backend implements.

A provider takes a frame path and a manifest, returns a structured dict of
signal values plus the model identifier. Errors surface as
:class:`ProviderError` rather than exceptions so the verdict layer can keep
going (one provider being down should still produce a verdict from the others).
"""

from __future__ import annotations

import base64
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from slate.manifest import Manifest


@dataclass(frozen=True)
class ProviderResult:
    """Result of one provider analyzing one frame.

    `signals` is the parsed JSON dict the model returned (after flattening one
    level of nesting). `error` is set when the call failed end-to-end; in that
    case `signals` will be empty and the verdict layer treats this as
    INDETERMINATE.
    """

    provider: str
    model: str
    signals: dict[str, Any]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class ProviderError(Exception):
    """Raised internally by providers; surfaced to caller as ProviderResult.error."""


class VLMProvider(Protocol):
    """Protocol for a vision-language model backend."""

    #: Short label used in verdicts (e.g. ``"gemma"``, ``"nvidia-primary"``).
    label: str
    #: Model identifier (e.g. ``"gemma4:latest"``).
    model: str

    def analyze_frame(self, frame_path: Path, manifest: Manifest) -> ProviderResult:
        """Send one frame + the manifest's prompt to the model. Return parsed signals."""
        ...


# ---------------------------------------------------------------------------
# Shared helpers (used by concrete providers)
# ---------------------------------------------------------------------------


def encode_image_b64(frame_path: Path, max_dim: int | None = None) -> str:
    """Read a frame from disk and return base64-encoded bytes.

    When ``max_dim`` is set (> 0), the image is downscaled so its longest side is
    at most ``max_dim`` pixels before encoding. Large frames (4K+) produce huge
    vision-token counts that dominate VLM latency and cost and, with local
    models, cause read timeouts; downscaling to ~1024px is effectively lossless
    for structural/quality judgments and cuts inference time by an order of
    magnitude. ``max_dim`` of ``None`` or ``<= 0`` sends the original bytes.

    Downscaling is best-effort: if the image cannot be opened or resized for any
    reason, the original bytes are encoded instead — the call never fails over a
    resize.
    """
    raw = frame_path.read_bytes()
    if not max_dim or max_dim <= 0:
        return base64.b64encode(raw).decode("ascii")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            longest = max(img.size)
            if longest <= max_dim:
                return base64.b64encode(raw).decode("ascii")
            scale = max_dim / longest
            new_size = (
                max(1, round(img.size[0] * scale)),
                max(1, round(img.size[1] * scale)),
            )
            buf = io.BytesIO()
            img.convert("RGB").resize(new_size, Image.Resampling.LANCZOS).save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return base64.b64encode(raw).decode("ascii")


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```\s*$", re.MULTILINE)


def parse_strict_json(raw: str, model_label: str) -> dict[str, Any]:
    """Parse strict-ish JSON from model output and flatten one nested level.

    Tolerates:
      * Markdown code fences (```...```)
      * Surrounding prose (extracts the outermost ``{...}`` block)

    Returns a flattened dict so providers that nest signals under CORRECTNESS /
    WARDROBE / etc. categories all look the same downstream. The
    ``response_quality`` object is preserved as a nested contract rather than
    flattened into signal keys. If parsing fails, returns
    ``{"error": <message>, "raw": <first 400 chars>}``.
    """
    text = raw.strip()
    text = _FENCE_RE.sub("", text).strip()
    if not text.startswith("{") and "{" in text and "}" in text:
        text = text[text.find("{") : text.rfind("}") + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"error": f"{model_label} did not return JSON", "raw": text[:400]}

    if not isinstance(parsed, dict):
        return {
            "error": f"{model_label} did not return a JSON object",
            "raw": str(parsed)[:400],
        }

    flat: dict[str, Any] = {}
    for key, value in parsed.items():
        if key == "response_quality":
            flat[key] = value
        elif isinstance(value, dict):
            flat.update(value)
        else:
            flat[key] = value
    return flat
