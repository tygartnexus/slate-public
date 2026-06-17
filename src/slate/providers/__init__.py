"""VLM provider implementations.

Each provider implements :class:`slate.providers.base.VLMProvider` and is
responsible for taking one frame + one Slate manifest and returning a
structured signal dict.
"""

from slate.providers.base import ProviderError, ProviderResult, VLMProvider
from slate.providers.gemma import GemmaProvider
from slate.providers.nvidia import NvidiaProvider

__all__ = [
    "GemmaProvider",
    "NvidiaProvider",
    "ProviderError",
    "ProviderResult",
    "VLMProvider",
]
