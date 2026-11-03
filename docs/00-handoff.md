# 00 — Handoff & Session Compact

Last updated: 2026-11-04
Status: **M6 complete — marketing site verified**
Next action: **M7 (faskes app), after your go-ahead**

## 1. What this project is

**Sehat Bridge** — a multi-tenant platform and web product for Indonesian health
facilities (faskes), with a SATUSEHAT integration that is real in shape but
mock-backed because production access requires a registered PT and faskes
onboarding.

- `backend/` — FastAPI JSON API, worker, migrations, SATUSEHAT adapter
- `frontend/` — Next.js 15 app: marketing site + faskes app + ops
- `tools/` — mock-satusehat, Playwright screenshot harness
- Repo: `~/github/sehat-bridge` (renamed from `Harisalghifary/simple-websocket`)

## 2. Locked decisions

| # | Decision | Reference |
|---|---|---|
| 1 | Name `sehat-bridge`, independent project, no Kemenkes affiliation | ADR-001 |
| 2 | Schema-per-tenant, `SET LOCAL search_path` only, RLS backup | ADR-002 |
| 3 | argon2id, not bcrypt | ADR-003 |
| 4 | Opaque rotating refresh tokens with family reuse detection | ADR-004 |
| 5 | Tenant from JWT `tid`, never from `X-Tenant-ID` alone | ADR-005 |
| 6 | Tenant DDL outside Alembic, replayed per schema + drift test | ADR-006 |
| 7 | Presigned POST with `content-length-range` + type conditions | ADR-007 |
| 8 | `aioboto3` against MinIO (S3 API) | ADR-008 |
| 9 | Redis is cache/ephemeral, never truth | ADR-009 |
| 10 | One `problem+json` error envelope | ADR-010 |
| 11 | ~~HTMX console~~ superseded by Next.js | ADR-011 → 016 |
| 12 | Mock-first SATUSEHAT via port/adapter, `live` by config | ADR-012 |
| 13 | Per-tenant encrypted credentials, separate `APP_ENCRYPTION_KEY` | ADR-013 |
| 14 | One tenant = one faskes, no facility hierarchy | ADR-014 |
| 15 | Monorepo split: API + frontend BFF | ADR-015 |
| 16 | Next.js single app (marketing + app + ops) | ADR-016 |
| 17 | Reset `simple-websocket` into this project, keep history | ADR-017 |
| 18 | Chainguard MinIO + S3-API bucket bootstrap (registry removal) | ADR-018 |

## 3. Scope boundary

**In:** tenancy, auth, roles, files, audit, mock SATUSEHAT sync, marketing site,
faskes app, ops, screenshots, docs.

**Out:** real SATUSEHAT traffic, clinical data (patients/encounters), NIK storage,
patient-facing app, blog/CMS, billing, realtime/WebSockets, SPA, dark mode, K8s.

If someone asks for clinical screens, the answer is: new milestone, new ADR, new
data model — not a UI addition.

## 4. Spec index

| File | Contents |
|---|---|
| `01-product.md` | Naming, disclaimer, personas, scope, success criteria, glossary |
| `02-architecture.md` | Components, lifecycle, tenancy, sessions, storage, adapter, ports/versions |
| `03-data-model.md` | Public + tenant schemas, RLS, migrations, leads, integration tables |
| `04-api-spec.md` | Endpoints, payloads, status codes, rate limits, versioning |
| `05-milestones.md` | M0–M10, tasks, acceptance criteria, demos |
| `06-testing-ops.md` | Test matrix, CI, observability, runbook, risks |
| `07-adrs.md` | ADR-001…017 + deferred decisions |
| `08-ui.md` | Marketing pages, app screens, ops, design system, a11y, budgets |
| `09-readme-and-demo.md` | README skeleton, 9 screenshots, demo script |
| `00-handoff.md` | This file |

## 5. Current state

- Repo renamed to `sehat-bridge`; `legacy/socket-chat` tag pushed; old working
  tree removed.
- `backend/` — FastAPI factory, settings, liveness/readiness, 5 unit tests,
  ruff + mypy clean, uv lockfile committed.
- `frontend/` — Next.js 15.5, React 19, Tailwind 4, pnpm 10; placeholder page
  renders API status server-side; `/api/ping` proves a first-party cookie through
  Caddy; lint, typecheck, and production build pass.
- Compose stack — postgres 16, redis 7, minio (Chainguard digest) + S3-API
  bucket/CORS bootstrap, mailpit, backend, frontend, caddy, mock-satusehat;
  `docker compose config` valid.
- `make test` green; `make smoke` green against the running stack.
- Readiness verified: all `ok`; stopping Redis returns `503` with `redis: error`
  and recovers to `200` after restart.
- MinIO bucket bootstrap exits `0`; API-level CORS returns the site origin.
- CI workflow, Makefile, `.env.example`, README, LICENSE, docs copied.

### M1 — tenancy

- Public schema in Alembic (`0001_public_baseline`): tenants, users,
  memberships, refresh_tokens, audit_log, leads.
- Tenant schema in `tenant_migrations/0001_init.sql`; applied per schema with
  search_path scoped to the transaction.
- Provisioning CLI (`make tenant`), fan-out (`make migrate-tenants`), seed with
  two tenants and one identity shared across both.
- Runtime connects as `sehat_app`, which owns nothing; RLS with `FORCE` returns
  zero rows when `app.tenant_id` is unset.
- Tenant middleware resolves the `X-Tenant-ID` hint through Redis + Postgres.
- Six integration tests: idempotent provisioning, interleaved pool isolation,
  RLS denial, failed-provisioning cleanup, schema drift, migration re-run.
- `scripts/check_tenant_safety.py` fails CI on session-level `search_path`.

### M2 — authentication

- argon2id via `pwdlib`; uniform `invalid_credentials` with a dummy verify on
  unknown emails so timing matches.
- Access token: HS256, 15 min, claims `iss/aud/sub/tid/role/scope/fid/jti`.
- Refresh token: opaque, SHA-256 at rest, rotated on use, family reuse revokes
  the whole chain and writes `auth.refresh_reuse`.
- Logout blacklists the `jti` in Redis for its remaining lifetime.
- Rate limits: login 5/5 min per tenant+email, register 10/hour per IP,
  refresh 30/hour per token, `429` with `Retry-After`.
- Platform login issues a tenant-less token with `scope=platform`; refresh tokens
  for it are nullable-tenant (migration `0002_platform_refresh`).
- `/users/me` returns the user, membership, and profile.
- Audit events verified live: login, login_failed, refresh, refresh_reuse,
  logout, platform_login, register.
- 8 auth integration tests + 4 security unit tests; full suite 18 unit and
  14 integration.

### M3 — users and roles

- `GET /users` is cursor-paginated (keyset on `created_at, user_id`), admin+,
  with profile display names joined from the tenant schema.
- `PATCH /users/{id}/role` enforces: members cannot grant roles, admins cannot
  touch owners or grant owner, and the last owner cannot be demoted (`409
  last_owner`).
- Cross-tenant user ids return `404 user_not_found`, not `403`.
- `PATCH /users/me` updates display name, IANA timezone (validated), and avatar
  reference; every access goes through the tenant session.
- Role changes write `user.role_changed` audit rows with before/after values.
- Shared identity verified: one email, two tenants, different roles and profiles.
- 8 user/role integration tests; suite now 19 unit and 22 integration.

### M4 — files and object storage

- `app/storage.py` wraps `aioboto3`; server calls use the internal MinIO
  endpoint, while presigned URLs are signed against `MINIO_PUBLIC_URL` so the
  browser can reach them.
- `POST /files/presign-upload` inserts an `uploading` row (the quota
  reservation), then returns a presigned POST whose policy pins
  `content-length-range` to the exact reserved size and the `Content-Type`.
- Quota is serialised per tenant with an advisory lock and excludes `deleted`
  rows; oversize/wrong-type bodies are rejected by MinIO itself.
- `POST /files/{id}/complete` checks expiry, `HEAD`s the object, verifies size
  and type, streams SHA-256, and transitions `uploading → ready`. Missing object
  is `404 object_not_found`; a second completion is `409 already_completed`.
- `GET /files/{id}/download` issues a 5-minute presigned GET; cross-tenant ids
  return `404` with no URL.
- `GET /files` is cursor-paginated; members see only their own files, admins can
  filter by `owner`, and deleted rows are hidden unless requested.
- `DELETE /files/{id}` is idempotent, soft-deletes the row, removes the object,
  and audits `file.deleted`.
- `make sweep` deletes expired `uploading` rows and releases their quota.
- CORS is proven by preflight and an `Origin`-tagged upload from the site
  origin; 25 MB+ objects fail at MinIO with `EntityTooLarge`.
- 10 file integration tests; suite now 19 unit and 32 integration.

### M5 — SATUSEHAT adapter and outbox

- `SatusehatPort` with `mock` (default) and `live` adapters; both pass a runtime
  protocol/contract test, and mode selection is configuration only.
- Mock service (`tools/mock-satusehat`) serves an OAuth2 token endpoint and
  FHIR-shaped `Organization`/`Patient` resources, with `?fail=500|4xx|timeout`.
- Credentials live per tenant; `client_secret` is Fernet-encrypted with a key
  derived from `APP_ENCRYPTION_KEY`. API returns only `has_secret`.
- `0002_integrations.sql` adds credentials, jobs, and mappings; `0003` replaces
  the original per-status uniqueness with a partial unique index on active jobs
  so repeated failures keep history.
- Outbox worker: transactional enqueue, idempotent mapping short-circuit,
  exponential backoff, max 5 → `dead`, 4xx → `failed`, stale `running` recovery,
  one job per tenant per cycle.
- REST surface: credentials GET/PUT, test connection, enqueue, job list/detail;
  cross-tenant ids return `404`.
- `make worker`, `make worker-once`, and `make integration-demo` (Compose worker
  so internal mock DNS works).
- Secrets verified absent from responses, audit metadata, and captured logs.
- 9 integration tests + 7 unit tests; suite now 26 unit and 41 integration.

### M6 — marketing site

- Design tokens and type scale live in `app/globals.css`; Plus Jakarta Sans via
  `next/font`; reduced-motion and visible focus styles are global.
- Marketing shell: sticky nav with a focus-trapped mobile dialog, footer with
  contact and disclaimer, skip link, and `(marketing)` route group.
- Seven pages: `/`, `/solusi`, `/integrasi`, `/demo`, `/tentang`, `/faq`,
  `/privasi`, plus branded 404 and 500 and a temporary `/masuk`.
- Product visuals are literal HTML UI compositions labelled as illustrations —
  no stock photos, no fake customer logos or testimonials.
- Per-page metadata, canonical URLs, `sitemap.ts`, `robots.ts`, JSON-LD
  `Organization` + `SoftwareApplication`, and `next/og` images for every page.
- `POST /api/lead` (Next route handler) forwards to `/api/v1/leads`; the backend
  re-checks the honeypot and timing (`< 3 s`), rate limits per IP (5/h) and
  globally (100/h), and updates duplicate email+facility leads within 24 h.
- 6 lead integration tests; suite now 27 unit and 47 integration.
- Lighthouse mobile on the running stack: Performance 98, Accessibility 100,
  SEO 100, CLS 0. All six content pages also score 100 for accessibility/SEO.

## 6. Next action — M7

```bash
make up
make test
make test-integration
git add -A && git commit -m "feat(m6): marketing site and public lead capture"
git push origin main
```

M7 is the faskes app: cookie session BFF, login, dashboard, files, members,
integration, and profile pages. Stop after its gate and review before M8.

## 7. Open questions (non-blocking)

| Question | Default if unanswered |
|---|---|
| Deploy target (VPS, Fly, Render, K8s) | Compose-only for v0.1.0 |
| Demo phone/WhatsApp number | Placeholder `+62…`, clearly marked in `.env` |
| Legal entity name for `/tentang` | "Sehat Bridge (proyek independen)" |
| Custom domain | none; `NEXT_PUBLIC_SITE_URL` configurable |

## 8. Risks to watch

1. Writing a marketing claim we cannot defend (customer counts, ISO, Kemenkes).
2. Copying dhealth's copy or assets instead of using it as structure.
3. Tokens leaking into client components.
4. MinIO CORS forgotten → uploads fail with an opaque error.
5. `search_path` set with plain `SET` → cross-tenant leak.
6. Mock integration mistaken for production readiness.

## 9. How to resume

1. Read this file, then `01-product.md` and `05-milestones.md`.
2. Switch the agent out of Plan mode.
3. Confirm the current milestone gate; start the next one only after approval.
4. Do not start M5 until M4's demo passes on a clean machine.