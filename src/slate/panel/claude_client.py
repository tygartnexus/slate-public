"""Thin Anthropic SDK wrapper for the Panel personas.

Customers bring their own ``ANTHROPIC_API_KEY``. Slate never proxies the
key or the frames.

The wrapper exposes one method — :meth:`ClaudeVisionClient.analyze` —
which takes a prompt + a list of (frame_path, frame_name) pairs and returns
the raw response text. The provider-level prompt design and JSON parsing
live in each persona module so personas can evolve independently.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ClaudeResponse:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


DEFAULT_PANEL_MODEL = "claude-sonnet-4-6"


class ClaudeVisionClient:
    """Lazy Anthropic SDK wrapper. Constructs the underlying client on first use
    so tests can patch ``analyze`` without needing the SDK installed."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_PANEL_MODEL,
        api_key: str | None = None,
        max_tokens: int = 2000,
        timeout_seconds: int = 300,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or ""
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self._client: Any | None = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError as exc:  # pragma: no cover — dep is required
                raise RuntimeError(
                    "anthropic SDK not installed; install slate[dev] or "
                    "`pip install anthropic`"
                ) from exc
            self._client = Anthropic(api_key=self.api_key, timeout=self.timeout_seconds)
        return self._client

    def analyze(self, prompt: str, frames: list[Path]) -> ClaudeResponse:
        """Send one prompt plus up to ``len(frames)`` images to Claude.

        Returns the response text plus token usage. On any SDK error returns
        ``ClaudeResponse`` with ``error`` set; callers convert that into the
        persona's ``error`` field.
        """
        if not self.api_key:
            return ClaudeResponse(
                text="", model=self.model, error="ANTHROPIC_API_KEY not set"
            )

        content: list[dict[str, Any]] = []
        for frame in frames:
            try:
                b64 = base64.b64encode(frame.read_bytes()).decode("ascii")
            except OSError as exc:
                return ClaudeResponse(
                    text="", model=self.model, error=f"read {frame}: {exc}"
                )
            media_type = _media_type_for(frame)
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64,
                    },
                }
            )
        content.append({"type": "text", "text": prompt})

        try:
            client = self._ensure_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": content}],
            )
        except Exception as exc:
            return ClaudeResponse(text="", model=self.model, error=f"anthropic: {exc}")

        try:
            text_blocks = [
                block.text for block in response.content if getattr(block, "text", None)
            ]
            text = "\n".join(text_blocks).strip()
        except Exception as exc:
            return ClaudeResponse(
                text="", model=self.model, error=f"anthropic response parse: {exc}"
            )

        usage = getattr(response, "usage", None)
        return ClaudeResponse(
            text=text,
            model=self.model,
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
        )


def _media_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/png")
