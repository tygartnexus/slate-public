"""Compatibility shim for :mod:`slate.panel.personas`."""

from slate.panel.personas import (
    AnimatorPersona,
    AudiencePersona,
    ColorGraderPersona,
    DirectorPersona,
    Persona,
    default_panel_personas,
    run_persona,
)

default_pro_personas = default_panel_personas

__all__ = [
    "AnimatorPersona",
    "AudiencePersona",
    "ColorGraderPersona",
    "DirectorPersona",
    "Persona",
    "default_panel_personas",
    "default_pro_personas",
    "run_persona",
]
