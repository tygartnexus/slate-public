"""Default Panel personas + helpers to construct the standard ensemble."""

from slate.panel.personas.animator import AnimatorPersona
from slate.panel.personas.audience import AudiencePersona
from slate.panel.personas.base import Persona, run_persona
from slate.panel.personas.color_grader import ColorGraderPersona
from slate.panel.personas.director import DirectorPersona


def default_panel_personas() -> list[Persona]:
    """The default four-persona Panel ensemble."""
    return [
        DirectorPersona(),
        ColorGraderPersona(),
        AnimatorPersona(),
        AudiencePersona(),
    ]


__all__ = [
    "AnimatorPersona",
    "AudiencePersona",
    "ColorGraderPersona",
    "DirectorPersona",
    "Persona",
    "default_panel_personas",
    "run_persona",
]
