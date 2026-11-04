# 05 — Milestones

Estimates are focused engineering days. Each milestone leaves `main` green: **no
milestone may leave the test suite failing.** M0–M2 are the critical path.

| Milestone | Theme | Estimate | Depends on |
|---|---|---|---|
| M0 | Bootstrap, repo reset & dev env | 0.75d | — |
| M1 | Tenancy foundation | 1.5d | M0 |
| M2 | Authentication | 1.5d | M1 |
| M3 | Profiles, users & roles | 1d | M2 |
| M4 | Files & object storage | 1.5d | M3 |
| M5 | SATUSEHAT adapter (mock) | 1.5d | M4 |
| M6 | Marketing site | 2.5d | M0 |
| M7 | Faskes app | 2.5d | M5 |
| M8 | Ops console | 1d | M7 |
| M9 | Hardening & operations | 1.5d | M8 |
| M10 | Screenshots, docs & v0.1.0 | 1.5d | M9 |

Total ≈ **17 focused days**, plus buffer.

**Parallelism:** M6 can start once M0 lands and does not depend on the backend
milestones. If two people work, M6 runs alongside M1–M5. If one person, follow the
order above; the marketing site is a welcome break after the tenancy work.

---

## M0 — Bootstrap, repo reset & dev environment

**Goal:** a new dev goes from clone to a running marketing page and a green health
check in under five minutes.

Repo handling
- [ ] `gh repo rename sehat-bridge` (confirm the new URL), then rename the local
      directory and remote
- [ ] Tag the current state `legacy/socket-chat` and push it, so the old
      Express/Socket.IO demo is recoverable
- [ ] Remove `src/`, `dist/`, `node_modules/`, `package-lock.json`, `tsconfig.json`
      from the working tree in the first commit (history keeps them)
- [ ] New root: `backend/`, `frontend/`, `tools/`, `docs/`, `compose/`

Scaffolding
- [ ] Backend: uv project, Python 3.12, ruff, mypy, FastAPI app factory, lifespan
- [ ] Frontend: `create-next-app` with **pnpm** (TypeScript, App Router,
      Tailwind, ESLint), `output: "standalone"`, `.nvmrc` (Node 20), one
      placeholder page
- [ ] `docker-compose.yml`: postgres:16, redis:7, minio (Chainguard build) +
      bucket/CORS bootstrap, mailpit, backend, frontend, caddy, `mock-satusehat` stub
- [ ] Caddy: `/` → frontend:3000, `/api/*` → backend:8000, no path rewriting
- [ ] MinIO CORS configured for the site origin (`POST`, `GET`, presigned form)
- [ ] `Makefile`: `up down logs migrate tenant seed test lint fmt worker demo screenshots`
- [ ] CI: backend job (ruff, mypy, pytest) + frontend job (eslint, tsc, build)
- [ ] `docs/` receives this spec set; `README.md` disclaimer line

Acceptance
- `make up && make test` green on a clean machine
- `make smoke` passes: frontend 200, all three dependencies `ok`, API docs 200,
  and an `HttpOnly` cookie set by the frontend through Caddy
- `curl localhost:8080/` returns the Next.js page; `curl localhost:8080/api/v1/health/ready` returns all dependencies `ok`
- A cookie set by the frontend is first-party through Caddy
- Stopping Redis flips readiness to 503; the marketing page still serves
- CI green on the first PR, both jobs

Demo: `make up && open http://localhost:8080`

---

## M1 — Tenancy foundation

**Goal:** prove the invariant — no request can see another tenant's schema.

Tasks
- [ ] `public` Alembic baseline: `tenants`, `users`, `memberships`, `audit_log`, `leads`
- [ ] `tenant_migrations/0001_init.sql`: profiles, files, schema_migrations, RLS
      with `FORCE`, `app.tenant_id` setting
- [ ] `db/tenant_context.py` ContextVar + `get_tenant_session()` with
      `SET LOCAL search_path` **and** `SET LOCAL app.tenant_id`
- [ ] Non-owner DB role in compose init so RLS actually applies
- [ ] `TenantMiddleware` + Redis tenant cache (60s) + invalidation
- [ ] Provisioning service + `make tenant NAME=… OWNER=…`, advisory lock,
      `failed` state with reason, idempotent re-run
- [ ] `make migrate-tenants` fan-out, one transaction per tenant
- [ ] Drift test: fresh tenant vs seeded tenant, column by column
- [ ] `scripts/seed.py`: two faskes tenants, shared email, sample files

Acceptance
- Interleaved two-tenant requests on a 2-connection pool: **zero** bleed
- CI guard: no non-`LOCAL` `SET search_path` anywhere in `backend/app/`
- Re-running `make tenant` for an existing slug exits 0 and changes nothing
- Interrupted provisioning never leaves a schema visible as `active`
- RLS returns zero rows when `app.tenant_id` is unset

Demo: `make tenant NAME=klinik-sehat OWNER=a@b.co && make tenant NAME=lab-nusantara OWNER=g@b.co`

---

## M2 — Authentication

**Goal:** full credential lifecycle, safe against the usual JWT mistakes.

Tasks
- [ ] `pwdlib[argon2]` hashing, 12-char minimum
- [ ] Access token: `iss`, `aud`, `tid`, `role`, `jti`, 15 min
- [ ] Refresh token: opaque, hashed at rest, rotation, family reuse detection
- [ ] Redis `jti` blacklist, TTL = remaining lifetime
- [ ] `get_current_user` + `require_role(*roles)` dependencies
- [ ] `register` / `login` / `refresh` / `logout` / `platform-login`
- [ ] Uniform `invalid_credentials`, constant argon2 work on unknown email
- [ ] Rate limits on `login`, `register`, `platform-login`, `refresh`
- [ ] Audit rows for login, failure, logout, refresh reuse

Acceptance
- Login → refresh → reuse old refresh → whole family revoked
- Expired or blacklisted access token → 401
- Wrong tenant in body → `invalid_credentials`, latency parity ±20%
- Platform admin logs in with no tenant and gets `scope: platform`
- 6th login in 5 min → 429 with `Retry-After`

Demo: seed → login → `/users/me` → logout → retry → 401

---

## M3 — Profiles, users & roles

**Goal:** tenant-scoped member management with a sane permission model.

Tasks
- [ ] Profile upsert on registration; `GET/PATCH /users/me`
- [ ] `GET /users` (admin+) cursor paginated, membership + profile join
- [ ] `PATCH /users/{id}/role` with owner/admin rules from `04-api-spec.md §3`
- [ ] Last-owner protection (`409 last_owner`)
- [ ] Cross-tenant `user_id` → 404
- [ ] Shared-email test: one identity, two tenants, two roles, two profiles
- [ ] Profile access only through `get_tenant_session`

Acceptance
- Same email logs into both tenants and sees different profiles/roles
- Admin cannot demote the owner; last owner cannot be demoted
- Every role mutation appears in `audit_log`

Demo: role change as owner → 200; as member → 403

---

## M4 — Files & object storage

**Goal:** the end-to-end slice that exercises tenancy, auth, and MinIO.

Tasks
- [ ] `aioboto3` S3 client with separate internal/public endpoints
- [ ] Presigned **POST** with `content-length-range` + `Content-Type` conditions
- [ ] Bucket CORS verified from the browser origin (compose init, not manual)
- [ ] Quota reserved at presign, settled at `complete`, released on expiry
- [ ] `complete`: `HEAD`, size/type verify, SHA-256, status transition
- [ ] Presigned GET (5 min), keys under `tenants/{tid}/{file_id}/`
- [ ] Cursor-paginated list, soft delete + object removal
- [ ] Expired-upload sweeper (`make sweep`)

Acceptance
- 26 MB upload rejected by the policy itself, not app code
- Wrong `Content-Type` rejected by MinIO
- A browser upload from the site origin succeeds (CORS proven, not assumed)
- `complete` before upload → 404; double `complete` → 409
- Cross-tenant `file_id` → 404 and no URL issued
- Quota exhausted → 409 `quota_exceeded` at presign

Demo: presign → `curl -F` → complete → download opens the PDF

---

## M5 — SATUSEHAT adapter (mock-first)

**Goal:** a real integration pipeline that needs no Kemenkes approval.

Tasks
- [ ] `SatusehatPort` protocol: `issue_token`, `put_organization`, `put_patient`,
      `get_resource`
- [ ] `mock.py`: deterministic ids, OAuth2 token endpoint, FHIR-shaped responses,
      injectable failures (`?fail=500|timeout|4xx`)
- [ ] `mock-satusehat` service in compose (small FastAPI app, `tools/mock-satusehat/`)
- [ ] `live.py`: client-credentials token with Redis cache, FHIR R4 calls,
      selected only by `SATUSEHAT_MODE=live`
- [ ] Credentials service + Fernet encryption (`APP_ENCRYPTION_KEY`)
- [ ] `0002_integrations.sql`: credentials, `sync_jobs`, `sync_resources`
- [ ] Outbox: transactional enqueue, `make worker`, exponential backoff,
      max 5 attempts → `dead`, per-tenant fairness
- [ ] `test` connection endpoint and status transitions
- [ ] Integration REST endpoints from `04-api-spec.md §9`

Acceptance
- Full sync: credentials → test → sync organization → job `done` → mapping row
- Re-running the same sync is idempotent (same `fhir_id`, no duplicate job)
- Mock forced 500 → retries with backoff, then `dead` with `last_error`
- Forced 4xx → immediate `failed`, no retry
- Secret never appears in a response, log line, or audit metadata (grep test)
- Killing the worker mid-job leaves the job resumable
- Contract test: mock and live satisfy the same protocol

Demo: `make integration-demo` → token, job id, per-resource result table

---

## M6 — Marketing site

**Goal:** a credible public site that a hospital manager would trust — original
copy, real structure, fast on a phone.

Design system first (0.5d)
- [ ] Tokens: colour, type scale, spacing, radius, shadow, container widths
- [ ] Components: nav, footer, hero, section header, feature grid, module card,
      step list, stat block, testimonial, logo strip, CTA band, form fields
- [ ] Typography via `next/font`; no layout shift; `prefers-reduced-motion` honoured
- [ ] Dark sections limited to one band; no gradients-on-gradients

Pages
- [ ] `/` — hero, trust strip, workflow, ecosystem modules, features, stats,
      implementation steps, testimonials, CTA, footer
- [ ] `/solusi` — module detail by category with anchors
- [ ] `/integrasi` — SATUSEHAT, BPJS, LIS/RIS; honest "sedang disiapkan" states
- [ ] `/demo` — form (honeypot + timing), success and error states
- [ ] `/tentang` — company story, team placeholders, address
- [ ] `/faq` — accordion, 8–12 real questions
- [ ] `/privasi` — plain-language privacy policy covering leads and cookies
- [ ] 404 and 500 pages

Platform work
- [ ] `metadata` per page, canonical URLs, `sitemap.ts`, `robots.ts`
- [ ] JSON-LD `Organization` + `SoftwareApplication`
- [ ] Dynamic OG image per page (`next/og`)
- [ ] `POST /api/lead` route handler → backend `/api/v1/leads`
- [ ] WhatsApp/contact CTA wired to a real placeholder number
- [ ] Responsive 380 → 1440; mobile nav with focus trap

Content rules
- [ ] Original Indonesian copy; dhealth is a structural reference, not a source
- [ ] No copied logos, testimonials, or claims; fictional customers labelled
      "contoh" or removed
- [ ] No statistic we cannot defend; if illustrative, say so
- [ ] Disclaimer: independent project, not affiliated with Kemenkes

Acceptance
- Lighthouse mobile: Performance ≥ 90, Accessibility ≥ 95, SEO = 100
- All 7 pages render with JS disabled
- Demo form: valid submit → 202 and a lead row; honeypot → 202, no row;
  rapid resubmit → 429
- No layout shift (CLS < 0.1); images use `next/image` with dimensions
- `grep` finds no lorem ipsum, no TODO copy, no unlabelled fake numbers

Demo: `open http://localhost:8080` and submit the demo form

---

## M7 — Faskes app

**Goal:** the working product a clinic uses daily, backed only by real data.

Platform work
- [x] Session store (Redis), `__Host-sb_sid` cookie, `middleware.ts` guards
- [x] Route handlers: `POST/DELETE /api/session`, refresh, presign proxy
- [x] Server-side API client with problem+json → typed errors
- [x] 401 → refresh once → retry → redirect to `/masuk?next=…`
- [x] App shell: sidebar, tenant badge, mobile drawer, breadcrumbs, user menu
- [x] Empty, loading (skeletons), and error states for every screen

Screens
- [x] `/masuk`, `/daftar`, `/lupa-sandi` with inline validation
- [x] `/app/dasbor` — quota, file count, last sync, health, recent activity
- [x] `/app/berkas` — drag-drop presigned upload with progress, list, download, delete
- [x] `/app/anggota` — table, role change with last-owner error, invitation copy
- [x] `/app/integrasi` — credentials, test connection, sync, job history polling
- [x] `/app/profil` — display name, timezone, avatar
- [x] `/app/pengaturan` — minimal: locale display, timezone, sign out all sessions

Acceptance
- Full journey from a fresh browser: login → upload → complete → sync → results
- No fabricated data anywhere; every number traces to an API response
- Access token absent from HTML, client JS, localStorage, and logs
- Role-based nav hides items, and the API still returns 403 when typed directly
- Mobile 390px: tables become cards, touch targets ≥ 44px
- Upload works from the browser (MinIO CORS), with a readable failure message
- Keyboard-only pass on all five screens

Demo: log in as owner, upload, sync, then log in as member and hit a forbidden URL

---

## M8 — Ops console

**Goal:** the platform can be run without SQL.

Tasks
- [x] `/ops/masuk` using platform login (tenant-less token)
- [x] `/ops/tenant` — list, detail, provision, suspend/resume
- [x] `/ops/audit` — filter by tenant/action/date, read-only table
- [x] `/ops/kesehatan` — dependency status, version, uptime, job queue depth
- [x] Guard: non-admin gets 403 and no nav entry

Acceptance
- Provision tenant #3 in under 30 seconds, with a visible step timeline
- Suspended tenant: app shows a clear block page; login says `invalid_credentials`
- Audit table reflects every action from M2–M7
- Ops pages never leak one tenant's data to another

Demo: provision a tenant, suspend it, show the app block page

---

## M9 — Hardening & operations

**Goal:** safe to run for real users, diagnosable when it isn't.

Tasks
- [ ] Idempotency middleware (Redis, 24h, body hash)
- [ ] Audit retention job; lead retention job (12 months)
- [ ] Structured logs with `request_id`, `tenant_slug`, `user_id`, latency, no secrets
- [ ] OpenTelemetry trace + Prometheus metrics (backend and frontend)
- [ ] Error handling sweep: no bare `detail` in JSON routes; no stack traces in UI
- [ ] Email verification + password reset via Mailpit
- [ ] Tenant suspend/resume enforced at middleware level
- [ ] OpenAPI completeness test; contract diff in CI
- [ ] `docs/runbook.md`: rotate `SECRET_KEY`, re-wrap `APP_ENCRYPTION_KEY`, restore
      one tenant schema, drain or replay a stuck sync job

Acceptance
- Replayed `Idempotency-Key` returns identical body, no duplicate row
- One request → one log line with the same `request_id` as the response header
- Restore drill: dump one tenant schema → restore → drift check passes
- Rotation drill: re-wrap all secrets with a new key, test passes
- Chaos: Redis down (session loss handled), MinIO down (upload degrades only),
      mock SATUSEHAT down (jobs retry)

Demo: chaos pass + `make verify-tenant TENANT=klinik-sehat`

---

## M10 — Screenshots, docs & v0.1.0

**Goal:** someone else can run, understand, and evaluate it without you.

Tasks
- [ ] Screenshot harness (`tools/screenshots/`, Playwright) per `09-readme-and-demo.md`
- [ ] Marketing shots: beranda, solusi, integrasi (desktop + mobile)
- [ ] App shots: dasbor, berkas, integrasi, anggota, ops
- [ ] `README.md`: pitch, hero screenshot, disclaimer, architecture, quickstart,
      screenshot grid, status
- [ ] `docs/quickstart.md`, `api.md`, `satusehat.md`, `runbook.md`, `design-review.md`,
      `release.md`
- [ ] `scripts/demo.sh`: two tenants, forged header, RBAC denial, upload,
      mock sync with one forced failure
- [ ] ADRs finalised; ADR-016/017 recorded
- [ ] Tag `v0.1.0`, changelog, social preview uploaded

Acceptance
- A newcomer runs the quickstart and reaches the end of the demo
- `make demo` exits 0 with a pass/fail line per claim
- README under 220 lines, all images present and regenerable
- `docs/design-review.md` maps every source-document flaw to a fix or deferral

Demo: `make demo`

---

## Working agreements

- **Branching:** `feat/m1-tenancy`, one milestone per PR series; squash to `main`.
- **PR gate:** ruff, mypy, pytest, eslint, tsc, `next build`, plus two checklist
  lines: “did you touch `db/session.py`?” and “did you call SATUSEHAT outside
  `integrations/`?”.
- **Definition of done:** code + test + docs touch + audit event where the action
  is security-relevant.
- **UI definition of done:** keyboard pass, 390px pass, empty/loading/error states
  designed, no hard-coded copy.
- **No milestone bleed:** cut scope rather than parallelise the critical path.
- **Blockers escalate to a decision, not a hack:** record it as an ADR in the same PR.