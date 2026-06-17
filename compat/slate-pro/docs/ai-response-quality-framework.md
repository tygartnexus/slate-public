# AI Response Quality Framework

## Purpose

Slate Pro uses the shared Core contract from `slate.response_quality` so persona outputs cannot approve or block a render with unsupported prose. Every persona result, fused panel result, and enhanced verdict can carry facts, assumptions, unknowns, confidence, evidence, risks, counterarguments, recommendation, tradeoffs, and what would change the recommendation.

## Available Modes

Pro personas use `red_team` mode by default because their job is adversarial review. The shared contract also supports `standard`, `evidence_based`, `executive_memo`, `technical_review`, and `legal_risk_review` for downstream tools.

## Prompt Templates

Persona prompts import `build_response_quality_prompt()` and append the shared response-quality JSON contract. Prompt template text remains centralized in `slate.response_quality`:

- anti-hallucination checks
- red-team review
- CEO reality check
- evidence-based recommendations
- legal/compliance review
- technical architecture review
- bias detection
- executive decision matrix

## How To Extend

1. Add persona-specific criteria in `slate_pro.panel.personas.*`.
2. Keep the shared `response_quality` object required in every persona JSON response.
3. Reject malformed or incomplete persona JSON rather than accepting a partial answer.
4. Add tests for the new persona's prompt, parser behavior, risks, tradeoffs, and evidence export.

## Good Output

```json
{
  "publish_ready": false,
  "summary": "Animator blocks publish because the foot contact drifts.",
  "flags": [
    {
      "category": "motion",
      "severity": "critical",
      "frame": "frame_0042.png",
      "description": "Foot slides while body weight is planted."
    }
  ],
  "per_frame_notes": {
    "frame_0042.png": "Foot contact contradicts body weight."
  },
  "response_quality": {
    "facts": ["frame_0042.png shows visible foot slide"],
    "assumptions": ["sampled frames represent the shot"],
    "unknowns": ["in-between frames were not reviewed"],
    "confidence_score": 0.81,
    "evidence": ["frame_0042.png"],
    "risks": ["could be intentional stylization"],
    "counterarguments": ["other frames may read correctly in motion"],
    "recommendation": "block publish until motion is reviewed",
    "tradeoffs": ["blocking protects quality but slows delivery"],
    "what_would_change_recommendation": ["a full motion review showing the slide is not visible"]
  }
}
```

## Bad Output

```json
{
  "publish_ready": true,
  "summary": "Looks fine."
}
```

This is rejected because it omits the response-quality contract and provides no evidence or confidence.
