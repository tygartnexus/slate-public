"""Compatibility shim for :mod:`slate.panel`."""

from slate.panel import (
    DEFAULT_PANEL_MODEL,
    AnimatorPersona,
    AudiencePersona,
    ClaudeResponse,
    ClaudeVisionClient,
    ColorGraderPersona,
    DirectorPersona,
    EnhancedStatus,
    EnhancedVerdict,
    PanelVerdict,
    Persona,
    PersonaFlag,
    PersonaVerdict,
    default_panel_personas,
    fuse,
    run_panel,
)

DEFAULT_PRO_MODEL = DEFAULT_PANEL_MODEL

__all__ = [
    "DEFAULT_PANEL_MODEL",
    "DEFAULT_PRO_MODEL",
    "AnimatorPersona",
    "AudiencePersona",
    "ClaudeResponse",
    "ClaudeVisionClient",
    "ColorGraderPersona",
    "DirectorPersona",
    "EnhancedStatus",
    "EnhancedVerdict",
    "PanelVerdict",
    "Persona",
    "PersonaFlag",
    "PersonaVerdict",
    "default_panel_personas",
    "fuse",
    "run_panel",
]
