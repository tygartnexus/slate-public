# Launch copy drafts

Internal drafts for the free/open-source launch.

## Hacker News (Show HN)

**Title:** `Show HN: Slate - free tools for catching broken AI-generated animation`

**Body:**

I've spent the past six months building an automated cinematic pipeline that uses AI tools end-to-end: Daz characters into UE5, retargeted animations, Movie Render Queue, the works. Every time I shipped a clip, something embarrassing snuck through: a character lying horizontal mid-shot, a foot floating off the ground, a sideways walk cycle.

Slate is the verdict layer I should have built first.

- **Provider verdicts:** Slate samples render frames and checks them with the VLM providers you configure: local Gemma via Ollama, NVIDIA NIM with cross-check, or both.
- **Panel review:** an optional four-persona adversarial Panel (Director, Color Grader, Animator, Audience) tries to find reasons not to publish.
- **Evidence bundles and dashboard:** Slate can package verdict JSON, frame hashes, persona reports, and redacted raw outputs; the optional dashboard stores verdict JSON for history and comparisons.

There is no checkout, activation token, subscription, or paid upgrade. I do not think the product is mature enough to charge for, so Slate is free.

Pre-publish gate: only say packages are on PyPI after clean-environment install checks pass.

Repo and demo: https://slate.ai

## ProductHunt

**Tagline:** `Free pre-publish QA for AI-generated animation.`

**Description:**

Slate samples frames from AI-generated cinematic renders, checks them with configured vision-language providers, and can run a four-persona adversarial Panel that tries to find reasons not to publish. It targets failures render tools often miss: sideways characters, floating feet, broken hand poses, debug-pink textures, and lighting that fell out of the shot.

Slate, Panel review, evidence bundles, and the dashboard are MIT-licensed and free.

## Twitter / X thread

**Tweet 1:**

I've been building an automated cinematic pipeline with AI tools. Every clip had failure modes the render tools never caught: sideways characters, floaty feet, debug textures.

So I built Slate.

**Tweet 2:**

Slate samples render frames and checks them with configured VLM providers: local Gemma via Ollama, NVIDIA cloud lanes, or both.

Local mode keeps frames on your machine. Cloud model lanes use your own provider account.

**Tweet 3:**

Slate can add Panel review: Director, Color Grader, Animator, and Audience personas that try to find reasons not to publish.

It is free. No activation key.

**Tweet 4:**

Slate can also write evidence bundles: verdict JSON, frame hashes, Panel reports, optional thumbnails, and a raw-output redaction mode for external sharing.

**Tweet 5:**

There is no checkout, subscription, or paid upsell.

The product is not good enough to charge for yet, so Slate is MIT-licensed.

→ https://slate.ai
