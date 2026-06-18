# Slate Cloud

The free web dashboard for Slate verdicts. Users upload verdict JSON produced by
`slate`, view history, inspect detail pages, and compare saved runs side-by-side.

This repo is MIT-licensed. There is no checkout, billing portal, paid upgrade,
or license activation requirement.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│ Frontend (Next.js 16 + Tailwind, Vercel-ready)       │
│  - Clerk auth                                        │
│  - Verdict list / detail / compare                   │
│  - Free access status                                │
└──────────────────────────────────────────────────────┘
                          │
                          ▼  REST + Clerk JWT
┌──────────────────────────────────────────────────────┐
│ Backend (FastAPI, Fly.io / Railway-ready)            │
│  - /verdicts {POST list, GET id}                     │
│  - /accounts                                         │
│  - /ready                                            │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│ Postgres (Neon free tier viable for v1)              │
│  accounts, verdicts                                  │
└──────────────────────────────────────────────────────┘
```

Slate Cloud stores uploaded **verdict payload JSON** — not frame bytes and not API keys. That payload can still contain shot IDs, model observations, persona reports, manifest-derived fields, and other user-provided metadata that the customer chose to upload. Provider choice controls frame flow: local Ollama keeps sampled frames on the customer's hardware, while NVIDIA or Anthropic lanes send sampled frames to those providers through the customer's own account.

## Local dev

### Prereqs

- Python 3.10+
- Node.js 20+
- Docker (for the local Postgres)

### Backend

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
docker compose up -d postgres
alembic upgrade head
cp .env.example .env  # fill in CLERK_JWT_PUBLIC_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # fill in CLERK_* and NEXT_PUBLIC_API_URL
npm run dev   # http://localhost:3000
```

### Quick test (with backend up)

```bash
# Confirm deploy dependencies are configured and reachable
curl http://localhost:8000/ready

# Upload a verdict
curl -X POST http://localhost:8000/verdicts \
  -H "Authorization: Bearer $CLERK_JWT" \
  -H "Content-Type: application/json" \
  -d @verdict.json
```

## Deploy

See [docs/deployment.md](docs/deployment.md) for the production deploy.

## Access

All Slate Cloud dashboard functionality is free. The legacy `/billing/*`,
`/webhooks/stripe`, and `/account/license` routes return disabled compatibility
responses so stale clients cannot accidentally start a paid flow.

## License

MIT — see [LICENSE](LICENSE).
