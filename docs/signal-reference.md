# Signal reference

Slate's verdict is built from a set of structured signals each VLM provider returns. This page documents every signal Slate evaluates, what triggers a failure, and how to disable individual checks via the manifest.

## Categorical signals

These are booleans or enumerated values. A failure is recorded when the value crosses a hard line.

| Signal | Failure condition | Disable via manifest |
|---|---|---|
| `character_visible` | value is not `true` | `expected_characters[].must_be_visible: false` |
| `character_orientation` | value is one of `lying_horizontal`, `floating_mid_air`, `t_pose`, `ragdoll` | `expected_characters[].must_be_upright: false` |
| `character_pose_plausible` | value is `false` | always evaluated |
| `character_orientation_matches_movement` | value is `false` | always evaluated |
| `ground_contact_visible` | value is `false` | `expected_characters[].must_have_ground_contact: false` |
| `scale_plausible` | value is `false` | always evaluated |
| `landmark_visible` | value is `false` AND manifest has `expected_landmarks` | omit `expected_landmarks` to skip |
| `debug_quality_or_broken` | value is `true` | always evaluated |
| `wardrobe_present` | value is not `true` | `expected_characters[].must_have_wardrobe: false` |
| `head_covering_or_hair_present` | value is not `true` | `expected_characters[].must_have_hair_or_head_covering: false` |
| `character_identity_matches_manifest` | value is not `true` | `expected_characters[].must_match_identity: false` |
| `severity` | value is `blocking` | always evaluated |

## Quality signals (1-5 scale)

Each axis fails when the model's score is **below** the manifest's configured threshold for that axis. Default threshold is 3 (acceptable). Set an axis to `null` in the manifest to skip it.

| Signal | Default threshold | Disable |
|---|---|---|
| `lighting_quality` | 3 | `quality_thresholds.lighting: null` |
| `composition_quality` | 3 | `quality_thresholds.composition: null` |
| `atmosphere_quality` | 3 | `quality_thresholds.atmosphere: null` |
| `mood_readability` | 3 | `quality_thresholds.mood_readability: null` |
| `visual_coherence` | 3 | `quality_thresholds.visual_coherence: null` |

## Provider error signal

| Signal | When |
|---|---|
| `__provider_error__` | One provider could not be reached or returned malformed output. Surfaces as `VerdictStatus.INDETERMINATE` if there are no other content failures. |

## Manifest tuning examples

### Loosen the gate for previs (3 → 2)

```json
{
  "shot_id": "previs_42",
  "quality_thresholds": {
    "lighting": 2,
    "composition": 2,
    "atmosphere": 2
  }
}
```

### Tighten for studio publish (3 → 4)

```json
{
  "shot_id": "hero_001_publish",
  "quality_thresholds": {
    "lighting": 4,
    "composition": 4,
    "atmosphere": 4,
    "mood_readability": 4,
    "visual_coherence": 4
  }
}
```

### Disable wardrobe / identity (e.g. for stylized creature shots)

```json
{
  "shot_id": "dragon_flyover",
  "expected_characters": [
    {
      "id": "dragon",
      "description": "large winged reptile",
      "must_have_wardrobe": false,
      "must_have_hair_or_head_covering": false,
      "must_match_identity": false
    }
  ]
}
```
