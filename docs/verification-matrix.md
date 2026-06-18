# Slate Verification Matrix

Last updated: 2026-06-18

This matrix separates what is verified from what is only implemented, scaffolded,
or externally blocked. Do not broaden public claims beyond this table.

## Current Readiness Verdict

**Ready with caveats** for local development and repo evaluation.

**Blocked** for broad production-readiness claims until production deploy, real
Clerk browser auth, live NVIDIA, live Anthropic Panel, and benchmark evidence are
verified.

## Capability Status

| Capability | Status | Evidence | Missing evidence | Safe public claim |
|---|---|---|---|---|
| Core `slate verify` CLI | Tested locally + CI | Local `ruff`, `mypy`, `pytest`; local Gemma run produced structured verdict JSON. | Broader real-render benchmark suite. | Slate includes a locally tested CLI that produces structured verdicts from configured providers. |
| Local Ollama/Gemma provider | Tested locally | `gemma4:latest` local run completed after JSON-mode hardening. | Accuracy benchmark across representative renders. | Local Gemma can be used through Ollama; benchmark it on your own renders before relying on it. |
| NVIDIA provider | Built locally + unit tested | Provider tests and CLI wiring exist. | Live `NVIDIA_API_KEY` certification run. | NVIDIA integration exists; live certification requires a configured NVIDIA key. |
| Anthropic Panel provider | Built locally + unit tested | Panel client/persona tests exist. | Live `ANTHROPIC_API_KEY` Panel certification run. | Anthropic Panel integration exists; live certification requires a configured Anthropic key. |
| Local Panel provider | Built locally + unit tested | Local Ollama Panel client tests and JSON-mode payload exist. | Full live Core PASS -> local Panel E2E. | Local Panel mode exists; treat it as lower assurance until benchmarked. |
| Evidence bundles | Tested locally + CI | Bundle tests plus local `.tar.gz` certification artifact with verdict, manifest, hashes, environment, redaction metadata, and thumbnail. | Production artifact retention process. | Slate can build evidence bundles with verdict JSON, hashes, metadata, optional thumbnails, and redaction. |
| Response-quality contract | Tested locally + CI | Core, backend, and dashboard tests validate required sections, confidence, assumptions, risks, and placeholders. | Live-provider consistency benchmarks. | Slate enforces a response-quality contract for stored verdicts and generated summaries. |
| Cloud backend upload/list/detail/account | Tested locally + CI | FastAPI tests and local runtime with RS256 JWT verification. | Production database and deployed backend smoke. | Slate Cloud backend supports authenticated verdict upload and review APIs. |
| Dashboard verdict list/detail | Tested locally + CI/E2E | Playwright E2E with local auth bypass and live API. | Real Clerk browser sign-in. | Dashboard list/detail views are locally verified. |
| Dashboard comparison | Tested locally + E2E | Playwright seeds two verdicts and verifies side-by-side deltas. | Production browser smoke. | Dashboard can compare two saved verdicts side-by-side. |
| Free/no paid requirement | Tested locally + CI | Billing/license/webhook compatibility routes return disabled responses; copy has no paid tier. | Production smoke of disabled routes. | Slate is MIT-licensed and has no checkout, paid upgrade, or activation requirement in this repo. |
| Frame/data flow | Source-backed + partially tested | Cloud stores verdict payload JSON; local Ollama uses local daemon; provider code sends frames to configured providers. | Network-capture proof for local/cloud/provider lanes. | Slate sends sampled frames only to configured providers; Cloud stores verdict JSON, not frame files or provider keys. |
| Production deployment | Externally blocked | Deployment docs and readiness endpoint exist. | Production URL, Clerk app, database, env vars, and smoke evidence. | Production deployment is not yet verified. |
| Real Clerk browser auth | Externally blocked | Backend JWT verification tested with generated RS256 token. | Browser sign-up/sign-in through real Clerk app. | Clerk auth is implemented; real browser auth still needs production/staging verification. |
| Accuracy / benchmark claims | Unknown | Unit tests and one local model run. | Reproducible known-good/known-bad benchmark suite with provider results. | Do not publish accuracy percentages yet. |

## Claim Rules

- Do not claim **production ready** until production URLs, Clerk auth, database
  migrations, and dashboard/API smoke tests are verified.
- Do not claim **live NVIDIA certified** until the manual provider workflow
  passes with `NVIDIA_API_KEY`.
- Do not claim **live Anthropic Panel certified** until the manual provider
  workflow passes with `ANTHROPIC_API_KEY` and returns a real Panel result.
- Do not claim **accuracy rates** until benchmark artifacts exist.
- Do not say frames "never leave" a machine. Say frames go only to configured
  providers; local Ollama keeps frames local.
