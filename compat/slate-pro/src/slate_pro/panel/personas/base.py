"""Compatibility shim for :mod:`slate.panel.personas.base`."""

from slate.panel.personas.base import (
    Persona,
    VisionPanelClient,
    _clamp_severity,
    _parse_persona_json,
    run_persona,
)

__all__ = [
    "Persona",
    "VisionPanelClient",
    "_clamp_severity",
    "_parse_persona_json",
    "run_persona",
]
