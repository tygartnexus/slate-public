"""Create a small deterministic Slate certification fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = args.output
    frames = base / "frames"
    frames.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (256, 160), "#7fb3d5")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 105, 256, 160], fill="#5fa35f")
    draw.rectangle([45, 58, 112, 120], fill="#8b5a2b")
    draw.polygon([(38, 58), (78, 28), (120, 58)], fill="#6e2f21")
    draw.rectangle([155, 65, 172, 118], fill="#d7b899")
    draw.ellipse([150, 45, 177, 72], fill="#d7b899")
    draw.polygon([(148, 45), (178, 45), (163, 28)], fill="#f5f0dc")
    draw.line([163, 118, 160, 145], fill="#3d3d3d", width=4)
    draw.line([163, 118, 176, 145], fill="#3d3d3d", width=4)
    draw.line([155, 82, 135, 98], fill="#d7b899", width=4)
    draw.line([172, 82, 190, 98], fill="#d7b899", width=4)
    image.save(frames / "frame_0000.png")

    manifest = {
        "schema_version": "1.0",
        "shot_id": "certification_villager_001",
        "description": (
            "simple stylized medieval villager standing beside a small cottage "
            "on grass under blue sky"
        ),
        "expected_characters": [
            {
                "id": "hero",
                "description": (
                    "stylized medieval villager with light tunic and head covering"
                ),
                "must_be_visible": True,
                "must_be_upright": True,
                "must_have_ground_contact": True,
                "must_have_wardrobe": True,
                "must_have_hair_or_head_covering": True,
                "must_match_identity": True,
            }
        ],
        "expected_landmarks": ["small cottage", "grass"],
        "quality_thresholds": {
            "lighting": None,
            "composition": None,
            "atmosphere": None,
            "mood_readability": None,
            "visual_coherence": None,
        },
        "frame_sampling": {"mode": "explicit", "explicit_indices": [0]},
        "frame_count_expected": 1,
    }
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    print(base)


if __name__ == "__main__":
    main()
