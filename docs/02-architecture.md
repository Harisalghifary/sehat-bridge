# 02 — Architecture

## 1. Components

```
                    ┌──────────────────────────────┐
   browser ───────► │  frontend  (Next.js 15)      │  httpOnly cookie session
                    │  marketing + app + /ops      │  server-side BFF, no CORS
                    └───────────┬──────────────────┘
                                │ HTTP, bearer token from session
                    ┌───────────▼──────────────────┐
                    │  backend  (FastAPI, N workers)│
                    │  RequestID → Tenant → Auth    │
                    │  modules/{tenants,auth,users, │
                    │  files,audit,integrations}    │
                    └───┬────────────┬─────────────┘
                        │            │
              ┌─────────▼──┐  ┌──────▼──────┐  ┌────────────┐
              │PostgreSQL16│  │  Redis 7    │  │   MinIO    │
              │ public +   │  │ frontend    │  │ presigned  │
              │ tenant_*   │  │ sessions,   │  │ uploads    │
              │ schemas    │  │ cache,      │  │            │
              │            │  │ blacklist   │  │            │
              └────────────┘  └─────────────┘  └────────────┘
```

Two deployables, one repository:

- **`backend/`** — the JSON API, the worker, and migrations. Owns all business
  rules, tenant isolation, and the SATUSEHAT adapter. Knows nothing about HTML.
- **`frontend/`** — a Next.js 15 application (App Router, TypeScript) that serves
  the public marketing site, the authenticated faskes app, and `/ops`. Route
  handlers act as the BFF: they hold the cookie session and call `/api/v1` over
  HTTP with an access token stored server-side. No database access, no shared
  Python.

They sit behind one origin in Compose (Caddy: `/` → frontend, `/api` → backend),
so cookies are first-party and **the app/API path needs no CORS**. The single CORS
surface is the storage bucket, which must allow the site origin for direct
presigned uploads (§9.3). A deployment may split the two hosts later, at which
point API CORS becomes an explicit configured allowlist rather than an accident.

Redis is **cache and ephemeral state only** — losing it must never corrupt data.
It holds frontend sessions and backend token blacklists, but never a source of
truth. PostgreSQL is authoritative. MinIO holds blobs; metadata in Postgres
decides what exists.

## 2. Module layout

```
backend/
  app/
    main.py                  app factory, lifespan, /health, /metrics
    core/config.py           pydantic-settings, validated at boot
    core/security.py         argon2 hashing, JWT encode/decode, token generation
    core/crypto.py           Fernet for stored integration secrets
    core/errors.py           AppError hierarchy + problem+json handlers
    core/logging.py          structlog config, request_id binding
    core/deps.py             get_current_user, require_role, get_tenant_session
    db/engine.py             async engine + pool
    db/session.py            session factory, SET LOCAL search_path
    db/tenant_context.py     ContextVar holding resolved Tenant
    middleware/request_id.py  ULID per request, echoed in header + logs
    middleware/tenant.py      resolve tenant, reject mismatched header
    middleware/rate_limit.py  Redis sliding window, per tenant+subject
    modules/tenants/          models(public), provisioning, CLI
    modules/auth/             register/login/refresh/logout, token repository
    modules/users/            me, list, role change
    modules/files/            metadata, presign, complete, download
    modules/audit/            append-only writer, admin read
    modules/integrations/
      satusehat/port.py       SatusehatPort protocol (the ONLY boundary)
      satusehat/mock.py       deterministic fake: token + Organization/Patient
      satusehat/live.py       real FHIR R4 client (unused in v0.1.0)
      satusehat/service.py    credential resolution, outbox worker, retries
    api/v1/router.py          versioned JSON mounting
  alembic/                    public schema only
  tenant_migrations/          per-schema DDL, versioned
  workers/                    sync worker entrypoint

frontend/
  app/
    (marketing)/            /, /solusi, /integrasi, /demo, /tentang, /faq, /privasi
    (auth)/                 /masuk, /daftar, /lupa-sandi
    (app)/app/              dasbor, berkas, integrasi, anggota, profil
    (ops)/ops/              masuk, tenant, audit, kesehatan
    api/                    route handlers: session, refresh, upload, lead proxy
  components/               UI kit (shadcn/ui) + marketing sections + app shells
  lib/                      api client, session, format, copy dictionary
  messages/id.ts            all copy, no strings in components
  public/                   images, icons, OG assets
  middleware.ts             session guard for /app and /ops
  next.config.ts            standalone output, image domains

tools/
  mock-satusehat/            standalone mock FHIR service (compose + tests)
  screenshots/               Playwright capture harness

docs/  compose/  Makefile  docker-compose.yml
```

Rule: **backend routers may not import `db.session` directly.** They depend on
`get_tenant_session` only, so the tenancy invariant has one enforcement point.

Rule: **nothing outside `modules/integrations/satusehat/` may call SATUSEHAT.**
The worker, app requests, and tests all go through `SatusehatPort`.

Rule: **`frontend/` holds no domain logic and no database access.** If a screen
needs data the API does not expose, the fix is in the API, not a query in a view.
The frontend never imports `backend/` code — the boundary is HTTP, so it stays
a real boundary.

## 3. Request lifecycle (authenticated, tenant-scoped)

```
1. RequestIDMiddleware     assign ulid, bind to structlog context, set X-Request-ID
2. TenantMiddleware        slug = X-Tenant-ID (optional hint)
                           tenant = lookup(slug) via Redis cache → Postgres fallback
                           bind TenantContext (may be None for /health, /admin)
3. get_current_user        decode JWT, verify iss/aud/exp/signature
                           assert claims.tid == TenantContext.id        → else 403
                           load user + membership (cached 60s)
4. get_tenant_session      async with session.begin():
                             SET LOCAL search_path TO tenant_x, public
                             SET LOCAL app.tenant_id = '<uuid>'
                             yield session
5. handler                 domain logic
6. teardown                commit/rollback; connection returned clean
```

Why `SET LOCAL`: `SET` is session-scoped and **leaks through the pool**, which
is the classic cross-tenant breach in this architecture. `SET LOCAL` is reverted
at commit/rollback, so the next borrower of the connection inherits nothing.
Any code using raw `SET search_path` fails code review and a grep-based CI check.

## 4. Tenancy

### 4.1 Isolation strategy

Schema-per-tenant, chosen for hard physical separation and cheap per-tenant
backup/restore. Costs: migrations are O(tenants), cross-tenant analytics need
explicit unions, connection-level state must be managed carefully. Accepted for
this size; revisit above ~200 tenants (ADR-002).

### 4.2 Tenant resolution rules

| Situation | Source of truth |
|---|---|
| Authenticated request | JWT `tid` claim **MUST** equal `TenantContext.id` |
| Header present and mismatched | 403 `tenant_mismatch` (never auto-correct) |
| Header present, no token | Resolved for routing, but every protected route still requires auth |
| Login / register | `tenant_slug` in the request body only |
| Platform admin routes | No tenant context; explicit `public` schema queries |

Header-only tenancy (as in the source document) is spoofable and is rejected.
The header survives purely as a routing hint and a cheap early error.

### 4.3 Provisioning

PostgreSQL has no `CREATE SCHEMA … TEMPLATE` (that is Oracle/SQL Server).
Provisioning instead replays versioned, idempotent DDL:

```
1. advisory lock on hash(slug)                  -- serialise concurrent provisions
2. insert public.tenants(status='provisioning')
3. CREATE SCHEMA tenant_<slug>
4. for each file in tenant_migrations/ (sorted):
     run inside a transaction with search_path = tenant_<slug>
     record version in tenant_<slug>.schema_migrations
5. seed owner user + membership(role='owner')
6. set status='active', write audit_log
7. invalidate tenant cache key
```

Any failure rolls back the schema and marks the tenant `failed` with a reason, so
re-running is safe. `make tenant NAME=acme OWNER=a@b.c` wraps this.

### 4.4 Migration fan-out

`make migrate-tenants` applies pending files to every `active` tenant, one
transaction per tenant, in slug order, with progress output and a summary.
Idempotent and resumable. CI runs the drift test (see `03-data-model.md §5`).

## 5. Authentication

- **Passwords:** argon2id (`pwdlib`), tuned cost in config. bcrypt rejected —
  72-byte truncation and weaker modern margins (ADR-003).
- **Access token:** JWT HS256, 15 min, claims `iss, aud, sub, tid, role, jti,
  iat, exp`. `kid` header reserved for future key rotation.
- **Refresh token:** opaque `secrets.token_urlsafe(32)`, SHA-256 hashed at rest,
  30 days, rotated on every use, reuse revokes the whole family (ADR-004).
- **Logout:** `jti` written to Redis with TTL = remaining token lifetime; the
  auth dependency rejects blacklisted `jti`. Short expiry bounds the damage if
  Redis is unavailable — we fail **open** on logout only, closed on auth.
- **Login errors** are uniform (`invalid_credentials`) to avoid tenant/user
  enumeration. Timing is equalised by always running one argon2 verify.

## 6. Storage

- Presigned **POST** (S3 POST policy) with `content-length-range` and
  `Content-Type` conditions, so MinIO itself rejects oversize/wrong-type bodies.
- `MINIO_PUBLIC_URL` is separate from `MINIO_ENDPOINT`; presigned URLs are
  signed against the public host, or every local upload fails.
- Quota: reserved at presign time (`files.size_bytes` with `status='uploading'`),
  settled on `complete`, released on expiry by a sweeper.
- `complete` performs a `HEAD`, verifies size and content type, computes SHA-256,
  and flips `status='ready'`. Objects never become readable before that.
- Downloads are presigned GETs, 5 min, tenant-scoped keys only.

## 7. Cross-cutting contracts

### 7.1 Error envelope (`application/problem+json`)

```json
{
  "type": "https://seha.dev/errors/tenant_mismatch",
  "title": "Tenant mismatch",
  "status": 403,
  "code": "tenant_mismatch",
  "detail": "Token tenant does not match X-Tenant-ID",
  "trace_id": "01J8Z3Q9W7",
  "details": []
}
```

No handler may return a bare `detail` string. One exception handler maps
`AppError` and one maps unexpected exceptions (logging the trace, never leaking
internals).

### 7.2 Pagination

Cursor-based: `?limit=50&cursor=<opaque>`, response
`{"items": [...], "next_cursor": "...", "has_more": true}`.
Cursors encode `(created_at, id)`; no offsets, because tenant tables mutate.

### 7.3 Idempotency

`Idempotency-Key` on POST/PATCH: first request stores `{status, body_hash}` in
Redis for 24 h keyed by `tenant+subject+key`; a replay with a different body
returns 422 `idempotency_key_reuse`.

### 7.4 Configuration (fail-fast at boot)

| Variable | Notes |
|---|---|
| `POSTGRES_DSN` | asyncpg URL, required |
| `REDIS_DSN` | required |
| `MINIO_ENDPOINT` / `MINIO_PUBLIC_URL` | must differ in Docker |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` / `MINIO_BUCKET` | required |
| `SECRET_KEY` | ≥32 bytes, refused otherwise |
| `ACCESS_TOKEN_TTL_MINUTES` | default 15 |
| `REFRESH_TOKEN_TTL_DAYS` | default 30 |
| `PLATFORM_ADMIN_TOKEN` | CLI/admin only, never logged |
| `ENV` | `dev|test|prod`; prod refuses `SECRET_KEY=dev` |
| `RATE_LIMIT_*` | per-subject and per-tenant windows |

Frontend (`frontend/.env`):

| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_SITE_URL` | canonical origin, used for SEO, OG, and cookie scope |
| `API_BASE_URL` | server-side URL of the backend (`http://backend:8000`) |
| `SESSION_SECRET` | signs the session cookie; independent of `SECRET_KEY` |
| `REDIS_DSN` | same instance as backend, keys prefixed `sb:session:` |
| `NEXT_PUBLIC_MINIO_URL` | browser-facing S3 endpoint; must match bucket CORS |

## 8. Failure behaviour (must be explicit)

| Dependency down | Behaviour |
|---|---|
| Redis | Auth still works (blacklist check fails open); rate limiting fails closed to a conservative in-process limit; tenant cache falls back to Postgres |
| MinIO | File routes 503 `storage_unavailable`; auth/profile unaffected |
| Postgres | `/health/ready` 503; all data routes 503; process stays up |
| Migration failure on one tenant | That tenant marked `migration_failed`, others continue, job exits non-zero with a list |

## 9. Frontend (Next.js 15)

One application, four surfaces, three access levels:

| Surface | Routes | Rendering | Audience |
|---|---|---|---|
| Marketing | `/`, `/solusi`, `/integrasi`, `/demo`, `/tentang`, `/faq`, `/privasi` | static / ISR | public |
| Auth | `/masuk`, `/daftar`, `/lupa-sandi` | dynamic | public |
| App | `/app/dasbor`, `/app/berkas`, `/app/integrasi`, `/app/anggota`, `/app/profil` | server components | tenant member |
| Ops | `/ops/masuk`, `/ops/tenant`, `/ops/audit`, `/ops/kesehatan` | server components | platform admin |

Stack: Next.js 15 App Router, TypeScript, Tailwind CSS, shadcn/ui, Lucide icons,
`next/font` (Plus Jakarta Sans), Motion for restrained section reveals only.

### 9.1 Data flow and the token boundary

```
browser ──cookie(sid)──► Next.js server (RSC / route handler)
                              │  session = Redis[sid]
                              │  Authorization: Bearer <access_token>
                              ▼
                         FastAPI /api/v1
```

- Server Components call the API **directly on the server**, so no token ever
  reaches client JavaScript and no CORS is involved.
- Client Components never call the backend directly. When they need a mutation,
  they post to a Next.js route handler, which is the only place that touches the
  session.
- Route handlers: `POST /api/session` (login), `DELETE /api/session` (logout),
  `POST /api/session/refresh`, `POST /api/upload/presign`, `POST /api/lead`.
- On backend `401`, the server refreshes once with the stored refresh token and
  retries; on failure it clears the session and redirects to `/masuk?next=…`.
- `middleware.ts` guards `/app/*` and `/ops/*` by cookie presence only; real
  authorization is always re-checked by the API.

### 9.2 Sessions

Redis record, 30-minute sliding TTL:

```
{ user_id, tenant_id, tenant_slug, role, is_platform_admin,
  access_token, refresh_token, csrf, created_at }
```

Cookie: `__Host-sb_sid`, `Secure`, `HttpOnly`, `SameSite=Lax`, path `/`.

### 9.3 File uploads

Browser → MinIO directly, using a presigned POST obtained from a route handler
(which got it from the API). Requirements:

- MinIO bucket CORS must allow the site origin, `POST`, and the form content type.
  Without it, every upload fails with an opaque network error — configure it in
  Compose, not by hand.
- `content-length-range` still enforced by the storage policy.
- The route handler never proxies file bytes in v0.1.0.

### 9.4 Marketing site

- Content lives in `messages/id.ts` and typed TS data modules; no CMS in v0.1.0.
- SEO: per-page `metadata`, `sitemap.ts`, `robots.ts`, JSON-LD `Organization` +
  `SoftwareApplication`, dynamic OG images via `next/og`.
- The demo form writes to `POST /api/v1/leads` (public, rate-limited, honeypot +
  timing check). Success copy must not promise a response time we cannot keep.
- Copy is **original**. dhealth.co.id is a reference for structure and tone, not a
  template to duplicate — no copied text, logos, or testimonials. Fictional
  customer names in the MVP, or an explicit "contoh" label.
- Accessibility: semantic landmarks, skip link, focus-visible, 4.5:1 text
  contrast, `prefers-reduced-motion` respected.

### 9.5 Failure behaviour

| Failure | Behaviour |
|---|---|
| Backend down | Marketing pages still serve (static); `/app` shows an error boundary with retry and the request id; session preserved |
| Redis down | Session lost → redirect to login with a clear message; marketing unaffected |
| MinIO down | Upload UI shows `Penyimpanan sedang tidak tersedia`; other screens work |
| Next.js down | Caddy returns 502; `/api` and `/health` stay up |

## 10. SATUSEHAT integration

### 10.1 Why it is mock-first

SATUSEHAT production access requires a registered legal entity (PT), a faskes
record, and an onboarding agreement with Kemenkes. v0.1.0 therefore must not
depend on it. The adapter boundary means the same product code runs against a
local mock today and the real platform later.

### 10.2 Port

```python
class SatusehatPort(Protocol):
    async def issue_token(self, creds: Credentials) -> AccessToken: ...
    async def put_organization(self, token, org: OrganizationDraft) -> FhirRef: ...
    async def put_patient(self, token, patient: PatientDraft) -> FhirRef: ...
    async def get_resource(self, token, resource_type: str, rid: str) -> dict: ...
```

`mock` is deterministic: same input → same resource id, so tests can assert exact
ids and re-syncs are idempotent by construction. `live` implements the OAuth2
client-credentials flow and FHIR R4 calls against the configured base URL; it is
selected by `SATUSEHAT_MODE=live` and is exercised only by an opt-in test that
requires credentials, skipped by default.

### 10.3 Credentials

Per tenant, stored in the tenant schema, encrypted at rest:

| Field | Notes |
|---|---|
| `client_id` | plaintext, not secret |
| `client_secret_enc` | Fernet ciphertext, key from `APP_ENCRYPTION_KEY` |
| `organization_id` | SATUSEHAT organization reference |
| `base_url` | mock or live endpoint, per tenant |
| `status` | `unverified → connected → error` |
| `last_verified_at` | set by the "test connection" action |

Secrets are write-only through the API/app (never returned, only
`has_secret: true`), and never logged. `APP_ENCRYPTION_KEY` is separate from
`SECRET_KEY` so rotating signing keys does not orphan stored secrets.

### 10.4 Sync pipeline (outbox)

```
app "Sinkronkan sekarang" ──► enqueue sync_jobs(kind=organization|patient)
                            │
        worker loop (single asyncio task, poll 1s) ──► SatusehatPort
                            │
        success → sync_resources mapping (local_id ↔ fhir_id), job=done
        retryable (5xx, timeout) → exponential backoff, max 5, then dead
        terminal (4xx validation) → job=failed with response body
```

Properties that must hold:
- Enqueue is transactional with the data change (no lost jobs on crash).
- Re-running a job is idempotent: an existing mapping short-circuits, mock returns
  the same id, live uses `PUT` semantics.
- One poisoned tenant cannot starve the worker: fair round-robin, per-tenant
  concurrency cap of 1.
- The worker is a separate process (`make worker`) so an API restart does not lose
  in-flight work.

## 11. Local environment, ports & versions

| Service | Port | Notes |
|---|---|---|
| Caddy | 8080 | the only URL humans use (`http://localhost:8080`) |
| frontend (Next.js) | 3000 | not exposed directly in normal use |
| backend (FastAPI) | 8000 | `/api/v1/*`, `/health/*`, `/metrics` |
| mock-satusehat | 8090 | FHIR-shaped mock, `SATUSEHAT_MODE=mock` |
| PostgreSQL | 5432 | db `sehat`, non-owner app role |
| Redis | 6379 | shared; keys prefixed `sb:` |
| MinIO | 9000 / 9001 | API / console |
| Mailpit | 8025 | SMTP 1025, web UI 8025 |

Versions (pinned in lockfiles):

| Tool | Version |
|---|---|
| Python | 3.12 |
| uv | latest, `uv.lock` committed |
| Node | 20 LTS (`.nvmrc`) |
| pnpm | 10.x, `pnpm-lock.yaml` committed |
| Next.js | 15.x (App Router, `output: "standalone"`) |
| React | 19.x |
| Tailwind CSS | 4.x |
| PostgreSQL | 16 |
| Redis | 7 |
| MinIO | latest stable, pinned by digest in compose |

Rules:
- `pnpm` is the only package manager for `frontend/`; no `npm install` (it would
  produce a second lockfile and break CI).
- Every image is pinned by tag or digest; `latest` alone is not acceptable for
  Postgres, Redis, or MinIO.
- `.env.example` is the single source of truth for variable names; both services
  validate at boot and refuse to start on a missing required value.
