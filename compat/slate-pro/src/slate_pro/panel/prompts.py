"""Compatibility shim for :mod:`slate.panel.prompts`."""

from slate.panel.prompts import (
    PERSONA_OUTPUT_SCHEMA,
    PERSONA_RESPONSE_QUALITY_CONTRACT,
    build_persona_prompt,
)

__all__ = [
    "PERSONA_OUTPUT_SCHEMA",
    "PERSONA_RESPONSE_QUALITY_CONTRACT",
    "build_persona_prompt",
]
