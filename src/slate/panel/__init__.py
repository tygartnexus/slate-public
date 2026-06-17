"""Panel — adversarial persona ensemble for Slate."""

from slate.panel.claude_client import (
    DEFAULT_PANEL_MODEL,
    ClaudeResponse,
    ClaudeVisionClient,
)
from slate.panel.ensemble import run_panel
from slate.panel.fusion import fuse
from slate.panel.personas import (
    AnimatorPersona,
    AudiencePersona,
    ColorGraderPersona,
    DirectorPersona,
    Persona,
    default_panel_personas,
)
from slate.panel.verdict import (
    EnhancedStatus,
    EnhancedVerdict,
    PanelVerdict,
    PersonaFlag,
    PersonaVerdict,
)

__all__ = [
    "DEFAULT_PANEL_MODEL",
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
