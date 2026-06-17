"""Deprecated ``slate-pro`` console-script compatibility wrapper.

The product is now one free Slate package. This module intentionally delegates
to :mod:`slate.cli` instead of carrying a second CLI implementation.
"""

from __future__ import annotations

from slate.cli import app

__all__ = ["app"]


if __name__ == "__main__":  # pragma: no cover - module-as-script entrypoint
    app()
