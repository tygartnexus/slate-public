# Changelog

All notable changes to Slate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial repository skeleton carved out of the JonsStudio validation framework.
- `slate-ai` Python package layout with `pip install -e .` support.
- MIT license, README, .gitignore, CI workflow scaffold.
- Manifest schema (`slate.manifest`), verdict types (`slate.verdict`), signal definitions (`slate.signals`).
- VLM provider protocol (`slate.providers.base`) with local Gemma (Ollama) and NVIDIA NIM drivers.
- `slate verify` CLI entrypoint.
- Regression test fixtures for known-bad (all-black) and known-good frame sequences.

## [0.1.0] - TBD

First public alpha. Multi-VLM verdict on rendered frame sequences with a stable signal set.
