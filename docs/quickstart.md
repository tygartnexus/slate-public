# Quickstart

A 5-minute first run against a rendered frame sequence.

## 1. Write a manifest

Save this as `shot.json`:

```json
{
  "shot_id": "my_first_shot",
  "expected_characters": [
    {"id": "hero", "description": "humanoid character walking"}
  ],
  "expected_landmarks": ["village"]
}
```

This is a minimal Slate manifest. It says: there should be one upright humanoid visible in the frame, and the scene should show a village. Everything else uses defaults (see [signal-reference.md](signal-reference.md)).

## 2. Point at your frames

Slate accepts any directory containing `.png` / `.jpg` / `.tiff` frames named in sortable order (e.g. `frame_0000.png`, `frame_0001.png`, ...).

## 3. Run verify

```bash
slate verify --frames ./my_render --manifest shot.json
```

Slate samples three frames (first, middle, last), asks each configured VLM provider to evaluate them, applies the hard-fail rules, and prints a verdict:

```json
{
  "status": "PASS",
  "shot_id": "my_first_shot",
  "providers_consulted": ["gemma"],
  "frames_analyzed": ["frame_0000.png", "frame_0360.png", "frame_0719.png"],
  "failures": [],
  "quality_scores_aggregated": {
    "lighting_quality": 4.33,
    "composition_quality": 4.0,
    "atmosphere_quality": 4.0,
    "mood_readability": 4.0,
    "visual_coherence": 4.33
  }
}
```

## 4. What a failure looks like

If the render had a sideways character mid-shot, the verdict would be:

```json
{
  "status": "FAIL",
  "shot_id": "my_first_shot",
  "failures": [
    {
      "signal": "character_orientation",
      "value": "lying_horizontal",
      "frame": "frame_0360.png",
      "provider": "gemma",
      "model": "gemma4:latest",
      "description": "character is lying flat on the ground, not walking"
    }
  ]
}
```

The CLI also prints a human-readable summary table to stderr. Pipe the JSON to `jq` for ad-hoc filtering.

## 5. Wire it into your render pipeline

```bash
slate verify --frames ./renders/shot_42 --manifest ./shot_42.json --quiet --output verdict.json
case $? in
  0) echo "PASS — safe to publish" ;;
  1) echo "FAIL — see verdict.json" ; exit 1 ;;
  2) echo "INDETERMINATE — provider unreachable, retry later" ; exit 2 ;;
  *) echo "Slate error" ; exit 3 ;;
esac
```
