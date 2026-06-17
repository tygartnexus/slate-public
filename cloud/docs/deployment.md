# Slate Cloud — free dashboard deploy

## Hosting picks

| Component | Service | Why |
|---|---|---|
| Frontend | **Vercel** | Free tier viable for v1; Next.js native |
| Backend | **Fly.io** or **Railway** | Python-friendly; cheap; supports persistent volumes |
| Database | **Neon** (Postgres) | Free tier viable; branching for staging |
| Auth | **Clerk** | Lowest dev friction for authenticated dashboards |

Slate Cloud no longer processes payments or mints licenses. Do not configure
Stripe, issuer private keys, checkout links, or activation-token delivery for
this deployment.

## Production env vars (backend)

Set these in Fly/Railway dashboard:

```
DATABASE_URL            # Neon connection string
CLERK_JWT_PUBLIC_KEY    # from Clerk dashboard -> API keys -> JWT public key
```

After deploying the backend, check:

```bash
curl https://api.slate.ai/health
curl https://api.slate.ai/ready
```

`/health` only proves the process is running. `/ready` verifies required env
vars are present and the database can answer `SELECT 1`. Treat
`{"status":"blocked"}` as a deploy blocker.

## Production env vars (frontend, Vercel)

```
NEXT_PUBLIC_API_URL                 # https://api.slate.ai
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY   # Clerk publishable key
CLERK_SECRET_KEY                    # Clerk server-side secret key
NEXT_PUBLIC_SLATE_REPO_URL          # verified public Slate repo URL
```

## Database migrations

```bash
cd backend
alembic upgrade head
```

Run on every backend deploy. Add to the Fly/Railway deploy hook.

## Payment endpoints

The legacy endpoints remain disabled by design:

- `POST /billing/checkout` -> `410 payments_disabled`
- `POST /billing/portal` -> `410 payments_disabled`
- `POST /webhooks/stripe` -> `410 payments_disabled`
- `GET /account/license` -> `410 no license required`
