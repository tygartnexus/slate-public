# Release Certification

Use this runbook before claiming a Slate release is certified. A green build is
not enough for production readiness.

## Local Required Checks

Run from the repository root:

```bash
python -m ruff check src tests
python -m mypy src
python -m pytest -q
```

Run from `cloud/backend`:

```bash
python -m ruff check app tests
python -m mypy app
python -m pytest -q
```

Run from `cloud/frontend`:

```bash
npm ci
npm run check:content
npm run typecheck
npm run lint
npm run build
```

Run from `compat/slate-pro`:

```bash
python -m ruff check src tests
python -m mypy src
python -m pytest -q
```

## Local E2E Certification

1. Generate or reuse a local RS256 test token for the backend.
2. Run Alembic against a local database.
3. Start FastAPI with `CLERK_JWT_PUBLIC_KEY`.
4. Start Next.js with `SLATE_E2E_AUTH_BYPASS=true` and
   `SLATE_E2E_AUTH_TOKEN`.
5. Run:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3018 \
PLAYWRIGHT_API_URL=http://127.0.0.1:8018 \
SLATE_E2E_AUTH_TOKEN=<test-token> \
npm run test:e2e
```

This verifies dashboard list/detail, response-quality modes, and side-by-side
comparison against a live local API. It does not verify real Clerk browser auth.

## Manual Live Provider Certification

Use the `live-provider-certification` GitHub Actions workflow only after adding
the relevant repository secrets:

- `NVIDIA_API_KEY` for the NVIDIA lane.
- `ANTHROPIC_API_KEY` for the Anthropic Panel lane.

The workflow creates a fixture, runs `slate verify`, writes an evidence bundle,
and fails if provider errors or missing response-quality contracts are present.

## Production Certification

Production certification requires all of the following evidence:

- Frontend production URL loads.
- Backend `/health` returns `{"status":"ok"}`.
- Backend `/ready` returns `ready`.
- Real Clerk sign-up/sign-in produces a dashboard session without
  `SLATE_E2E_AUTH_BYPASS`.
- A real authenticated upload reaches `/verdicts`.
- Dashboard list/detail/compare pages display the uploaded verdicts.
- Legacy billing/license routes return disabled compatibility responses.
- Production database migration ran successfully.
- Error/log visibility is configured for frontend and backend.

Until these checks pass, the correct public status is **local/CI verified, not
production verified**.
