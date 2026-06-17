"""Deprecated compatibility package for Slate.

Panel review and evidence bundles now live in :mod:`slate`.
"""

__version__ = "0.1.0"

from slate.panel.verdict import (
    EnhancedStatus,
    EnhancedVerdict,
    PanelVerdict,
    PersonaFlag,
    PersonaVerdict,
)

__all__ = [
    "EnhancedStatus",
    "EnhancedVerdict",
    "PanelVerdict",
    "PersonaFlag",
    "PersonaVerdict",
    "__version__",
]
