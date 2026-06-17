# AI Response Quality Framework

## Purpose

Slate ships a reusable response-quality contract in `slate.response_quality`. The goal is to keep model judgments from sounding more certain than the evidence supports. AI outputs must separate facts, assumptions, unknowns, confidence, evidence, risks, counterarguments, recommendations, tradeoffs, and what would change the recommendation.

## Available Modes

- `standard`: concise answer with assumptions and confidence when needed.
- `evidence_based`: full evidence-first response.
- `red_team`: hostile review that leads with failure modes.
- `executive_memo`: CEO-style decision framing.
- `technical_review`: architecture/runtime/test risk review.
- `legal_risk_review`: issue-spotting with source and jurisdiction limits.

## Prompt Templates

Templates are centralized in `PROMPT_TEMPLATES`:

- `anti_hallucination`
- `red_team_review`
- `ceo_reality_check`
- `evidence_based_recommendation`
- `legal_compliance_review`
- `technical_architecture_review`
- `bias_detection`
- `executive_decision_matrix`

`build_response_quality_prompt()` injects the shared JSON contract into provider prompts. Frame-analysis prompts require a nested `response_quality` object, and the parser preserves that object instead of flattening it into signal fields.

## How To Extend

1. Add a new `ResponseMode` value only when it changes required behavior, not just wording.
2. Add or update a centralized prompt template in `slate.response_quality`.
3. Keep `ResponseQualityReport` backward-compatible unless a version bump is planned.
4. Add tests covering required sections, missing evidence, confidence bounds, and placeholder scans.

## Good Output

```json
{
  "response_quality": {
    "facts": ["frame_0000.png shows the primary character upright"],
    "assumptions": ["the manifest correctly describes the intended character"],
    "unknowns": ["unsampled frames were not inspected"],
    "confidence_score": 0.74,
    "evidence": ["provider=gemma", "frame=frame_0000.png"],
    "risks": ["the issue may occur between sampled frames"],
    "counterarguments": ["the sampled pose is readable"],
    "recommendation": "continue automated checks and keep human review for publish decisions",
    "tradeoffs": ["more sampled frames improve coverage but increase runtime"],
    "what_would_change_recommendation": ["a later sampled frame with a blocking signal"]
  }
}
```

## Bad Output

```json
{
  "summary": "Looks good. Ship it."
}
```

This is bad because it has no evidence, assumptions, unknowns, confidence, risks, counterarguments, tradeoffs, or change criteria.
