# Basic example

A minimal Slate run against a hypothetical medieval-village walk shot.

## Files

- `manifest.json` — describes what should be in the shot

## Running it

You need either:

- Ollama running locally with `gemma4:latest` pulled, OR
- `NVIDIA_API_KEY` set in your environment

Then point Slate at a directory of rendered frames:

```bash
slate verify \
  --frames /path/to/your/render \
  --manifest manifest.json
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0    | PASS — every signal passed for every analyzed frame |
| 1    | FAIL — at least one hard-fail signal triggered |
| 2    | INDETERMINATE — a provider was unreachable; treat with caution |
| 3    | Slate error (bad manifest, missing frames directory, etc.) |

## What Slate samples

With the default `first_mid_last` sampling, Slate analyzes 3 frames:

- frame index 0 (first)
- frame index `len // 2` (middle)
- frame index `len - 1` (last)

That's enough to catch whole-shot failures cheaply. For denser audits, switch the manifest's `frame_sampling.mode` to `every_n` (with a configurable stride) or `explicit` (hand-picked indices).
