"""Prompt construction — provider-agnostic.

The same prompt text is sent to every VLM. Only the *transport* differs
between providers (Ollama's ``/api/generate`` vs OpenAI-style chat completions).
"""

from __future__ import annotations

from slate.manifest import Manifest
from slate.response_quality import ResponseMode, build_response_quality_prompt


def build_frame_analysis_prompt(manifest: Manifest) -> str:
    """Build the VLM analysis prompt from a Slate manifest.

    The prompt instructs the model to return strict JSON with the categorical
    + numeric signals defined in :mod:`slate.signals`. The character
    description and landmark list are interpolated from the manifest.
    """
    primary = manifest.primary_character()
    character_desc = primary.description if primary else "humanoid character in the scene"
    landmarks = manifest.landmarks_text()
    shot_desc = manifest.description or "the rendered scene"

    return (
        "You are evaluating a cinematic frame. The expected character is "
        f"{character_desc}. The shot is: {shot_desc}. The scene should contain: "
        f"{landmarks}. Answer in STRICT JSON only (no markdown fences) with these "
        "keys. Do not infer or assume the character exists; if the character is "
        "not clearly visible in the pixels, set `character_visible=false`, "
        "`character_identity_matches_manifest=false`, `wardrobe_present=false`, "
        "and `head_covering_or_hair_present=false`.\n"
        "\n"
        "CORRECTNESS:\n"
        "  character_visible (true/false)\n"
        "  character_orientation (one of: upright_standing | upright_walking | "
        "upright_action_pose | lying_horizontal | floating_mid_air | t_pose | "
        "ragdoll | partial_offscreen | not_applicable)\n"
        "  character_pose_plausible (true/false)\n"
        "  character_orientation_matches_movement (true/false)\n"
        "  ground_contact_visible (true/false)\n"
        "  scale_plausible (true/false)\n"
        f"  landmark_visible (true/false) - does the scene show: {landmarks}?\n"
        "  debug_quality_or_broken (true/false) - Set to true ONLY if the image is corrupted, black, missing textures, or has checkerboard patterns. If the render is normal, set to false.\n"
        "\n"
        "WARDROBE / IDENTITY:\n"
        "  wardrobe_present (true/false) - is the character clearly clothed?\n"
        "  head_covering_or_hair_present (true/false) - does the character have "
        "hair or a head covering?\n"
        "  character_identity_matches_manifest (true/false) - does this look "
        f"like {character_desc}?\n"
        "\n"
        "SCENE QUALITY (1-5: 1=terrible, 3=acceptable, 5=excellent):\n"
        "  lighting_quality\n"
        "  composition_quality\n"
        "  atmosphere_quality\n"
        "  mood_readability\n"
        "  visual_coherence\n"
        "\n"
        "SUMMARY:\n"
        "  severity (one of: ok | minor_polish | blocking) - Set to ok unless there are critical rendering bugs.\n"
        "  description (one sentence - orientation, ground contact, mood)\n"
        "\n"
        + build_response_quality_prompt(
            mode=ResponseMode.EVIDENCE_BASED,
            subject="this single-frame visual analysis",
        )
    )
