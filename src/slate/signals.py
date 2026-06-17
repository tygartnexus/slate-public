"""Hard-fail signal definitions for Slate verdicts.

Signals come in two flavors:

* **Boolean / categorical** — `character_visible`, `character_orientation`, etc.
  These produce a `SignalFailure` when the provider's answer crosses a hard line
  (e.g. `character_orientation` ends up in :data:`BAD_ORIENTATIONS`).
* **Numeric quality** — `lighting_quality`, `composition_quality`, etc.
  These produce a `SignalFailure` when the value falls below the manifest's
  configured threshold.

The signal *names* themselves form the public contract Slate makes with VLM
providers: every provider is expected to emit a JSON object containing these
keys. The prompt in :mod:`slate.prompts` instructs the model accordingly.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Categorical / boolean signals
# ---------------------------------------------------------------------------

#: Orientations that are always a hard fail.
BAD_ORIENTATIONS: Final[frozenset[str]] = frozenset(
    {"lying_horizontal", "floating_mid_air", "t_pose", "ragdoll"}
)

#: Orientations that are acceptable in publish-tier output.
GOOD_ORIENTATIONS: Final[frozenset[str]] = frozenset(
    {
        "upright_standing",
        "upright_walking",
        "upright_action_pose",
        "partial_offscreen",
        "not_applicable",
    }
)

#: Severity values from the provider's `severity` field that hard-fail.
BLOCKING_SEVERITIES: Final[frozenset[str]] = frozenset({"blocking"})

# ---------------------------------------------------------------------------
# Numeric quality signals
# ---------------------------------------------------------------------------

#: Quality keys the provider returns on a 1-5 scale.
QUALITY_KEYS: Final[tuple[str, ...]] = (
    "lighting_quality",
    "composition_quality",
    "atmosphere_quality",
    "mood_readability",
    "visual_coherence",
)

# ---------------------------------------------------------------------------
# Signal identifiers (used in SignalFailure.signal)
# ---------------------------------------------------------------------------

SIGNAL_CHARACTER_VISIBLE: Final[str] = "character_visible"
SIGNAL_CHARACTER_ORIENTATION: Final[str] = "character_orientation"
SIGNAL_CHARACTER_POSE_PLAUSIBLE: Final[str] = "character_pose_plausible"
SIGNAL_CHARACTER_ORIENTATION_MATCHES_MOVEMENT: Final[str] = (
    "character_orientation_matches_movement"
)
SIGNAL_GROUND_CONTACT_VISIBLE: Final[str] = "ground_contact_visible"
SIGNAL_SCALE_PLAUSIBLE: Final[str] = "scale_plausible"
SIGNAL_LANDMARK_VISIBLE: Final[str] = "landmark_visible"
SIGNAL_DEBUG_QUALITY_OR_BROKEN: Final[str] = "debug_quality_or_broken"
SIGNAL_WARDROBE_PRESENT: Final[str] = "wardrobe_present"
SIGNAL_HEAD_COVERING_OR_HAIR_PRESENT: Final[str] = "head_covering_or_hair_present"
SIGNAL_CHARACTER_IDENTITY_MATCHES_MANIFEST: Final[str] = (
    "character_identity_matches_manifest"
)
SIGNAL_SEVERITY: Final[str] = "severity"

#: Every categorical signal Slate evaluates.
ALL_CATEGORICAL_SIGNALS: Final[tuple[str, ...]] = (
    SIGNAL_CHARACTER_VISIBLE,
    SIGNAL_CHARACTER_ORIENTATION,
    SIGNAL_CHARACTER_POSE_PLAUSIBLE,
    SIGNAL_CHARACTER_ORIENTATION_MATCHES_MOVEMENT,
    SIGNAL_GROUND_CONTACT_VISIBLE,
    SIGNAL_SCALE_PLAUSIBLE,
    SIGNAL_LANDMARK_VISIBLE,
    SIGNAL_DEBUG_QUALITY_OR_BROKEN,
    SIGNAL_WARDROBE_PRESENT,
    SIGNAL_HEAD_COVERING_OR_HAIR_PRESENT,
    SIGNAL_CHARACTER_IDENTITY_MATCHES_MANIFEST,
    SIGNAL_SEVERITY,
)
