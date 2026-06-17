"""Compatibility shim for :mod:`slate.panel.claude_client`."""

from slate.panel.claude_client import (
    DEFAULT_PANEL_MODEL,
    ClaudeResponse,
    ClaudeVisionClient,
    _media_type_for,
)

DEFAULT_PRO_MODEL = DEFAULT_PANEL_MODEL

__all__ = [
    "DEFAULT_PANEL_MODEL",
    "DEFAULT_PRO_MODEL",
    "ClaudeResponse",
    "ClaudeVisionClient",
    "_media_type_for",
]
