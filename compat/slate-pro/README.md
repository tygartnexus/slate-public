# Slate compatibility wrapper

`slate-pro` is deprecated. Panel review, evidence bundles, local/Anthropic panel providers, and the response-quality framework now live in the single free `slate-ai` package.

Use:

```bash
pip install slate-ai
slate verify --frames ./frames --manifest ./shot.json --panel --bundle evidence.tar.gz
slate bundle --verdict verdict.json --manifest ./shot.json --frames ./frames --output evidence.tar.gz
```

The `slate-pro` console script remains as a compatibility alias for the unified `slate` CLI, but new scripts and docs should use `slate`.

There is no checkout, activation token, subscription, or paid upgrade. The code is MIT-licensed.

## Import Compatibility

Common historical imports such as `slate_pro.panel.verdict` and `slate_pro.evidence.bundle` delegate to the implementation in `slate`. They exist only to give older integrations time to migrate.

## License

MIT - see [LICENSE](LICENSE).
