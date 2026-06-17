"""Small config helpers — env-var driven with sensible defaults.

Slate does not require any config file. Everything is either:

* a CLI flag,
* an environment variable, or
* a manifest field (preferred for per-shot settings).

This module just centralizes the env-var names so they're not scattered.
"""

from __future__ import annotations

import os


def env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"", "0", "false", "no", "off"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


# Provider selection — "gemma", "nvidia", "both", "auto" (auto = both if
# NVIDIA_API_KEY is set, else gemma).
DEFAULT_PROVIDER_SELECTION = "auto"

# NVIDIA cross-check on/off (when provider selection includes nvidia).
NVIDIA_CROSSCHECK_DEFAULT = True


# Downscale frames so the longest side is <= this many pixels before sending to
# a VLM. Large frames (4K+) inflate vision-token counts -> slow, costly, and
# (with local models) prone to read timeouts. 0 disables downscaling.
# Override via SLATE_MAX_IMAGE_DIM.
DEFAULT_MAX_IMAGE_DIM = 1024


def max_image_dim() -> int:
    return env_int("SLATE_MAX_IMAGE_DIM", DEFAULT_MAX_IMAGE_DIM)


# Per-provider HTTP read timeout in seconds. Override via SLATE_PROVIDER_TIMEOUT.
DEFAULT_PROVIDER_TIMEOUT = 300


def provider_timeout() -> int:
    return env_int("SLATE_PROVIDER_TIMEOUT", DEFAULT_PROVIDER_TIMEOUT)
