# 07 — Architecture Decision Records

Format: Context → Decision → Consequences → Status. Each ADR is one page in
`docs/adr/` once implemented.

---

## ADR-001 — Repository name and shape

**Context:** The source PDF is titled “Seha Backend”. “Seha” (صحّة) means health,
but the document contains no health-domain requirements, so the name is a project
label, not a product spec. `-backend` implies a sibling frontend that may never
exist.

**Decision:** Monorepo root named **`sehat-bridge`**, product name "Sehat
Bridge", with `backend/` inside. Chosen over `satusehat-bridge` to avoid implying
Kemenkes affiliation; "bridge" states the product's job. A mandatory disclaimer
appears in the README, site footer, and OpenAPI description.

**Consequences:** Renaming later touches CI, image tags, and DB names but is
otherwise cheap. No SATUSEHAT logo or wordmark is used anywhere.

**Status:** Accepted.

---

## ADR-002 — Schema-per-tenant isolation

**Context:** Three options: schema-per-tenant, database-per-tenant, single schema
with `tenant_id` + RLS.

**Decision:** Schema-per-tenant. Chosen for hard physical separation, per-tenant
`pg_dump`/restore, and low blast radius from a query bug.

**Consequences:**
- Migrations are O(tenants); mitigated by replayable versioned SQL + drift test.
- Connection state must be strictly transaction-scoped (`SET LOCAL`), or the pool
  becomes a leak vector.
- Cross-tenant analytics require explicit schema unions.
- Escape hatch at ~200 tenants: single-schema + RLS mode behind the same
  repository interface.

**Status:** Accepted.

---

## ADR-003 — argon2id instead of bcrypt

**Context:** The source document specifies bcrypt. bcrypt truncates at 72 bytes
and offers less modern margin.

**Decision:** argon2id via `pwdlib`, parameters stored in the hash string so they
can be tuned and rehashed on login.

**Consequences:** Slightly higher CPU per login (bounded by rate limits). The
`hashed_password` column is `text`, not a fixed width, to allow future schemes.

**Status:** Accepted.

---

## ADR-004 — Opaque rotating refresh tokens, not refresh JWTs

**Context:** A refresh JWT can only be revoked by blacklisting, which requires
state anyway.

**Decision:** Opaque 256-bit token, SHA-256 hashed at rest, rotated per use, with
`family_id` reuse detection that revokes the chain.

**Consequences:** One DB read per refresh (acceptable). A stolen token used after
legitimate rotation is detected and kills the session rather than silently
extending it.

**Status:** Accepted.

---

## ADR-005 — Tenant identity comes from the JWT, never the header

**Context:** The source design resolves the tenant from `X-Tenant-ID` alone,
which lets any authenticated user address another tenant's schema.

**Decision:** The token's `tid` claim is authoritative. A mismatched header is a
403; a missing header is fine. Login/register take `tenant_slug` in the body.

**Consequences:** Clients cannot “switch tenant” by changing a header — they must
re-authenticate or exchange a per-tenant token. That is the intended security
property.

**Status:** Accepted.

---

## ADR-006 — Tenant DDL outside Alembic

**Context:** Running Alembic's version table across dynamically created schemas
either needs N `version_table` configs or produces a single global version that
lies about per-schema state.

**Decision:** Plain, ordered, idempotent SQL in `tenant_migrations/`, recorded in
each schema's `schema_migrations`. Alembic owns `public` only. A CI drift test
compares every tenant's columns to a freshly provisioned schema.

**Consequences:** Two migration mechanisms to learn, but each is simple and
truthful. No hidden autogenerate diffs against N schemas.

**Status:** Accepted.

---

## ADR-007 — Presigned POST with policy constraints

**Context:** Presigned PUT cannot enforce a maximum object size from the server
side; a client can upload arbitrarily large bodies after signing.

**Decision:** Presigned POST with `content-length-range` and `Content-Type`
conditions, so MinIO rejects invalid uploads itself. `complete` re-verifies via
`HEAD` and records SHA-256.

**Consequences:** Clients use multipart form upload (more verbose than PUT) and
must send fields in order. In exchange, quota and MIME enforcement are real.

**Status:** Accepted.

---

## ADR-008 — MinIO over S3 SDK via `aioboto3`

**Context:** The official MinIO Python SDK is synchronous; calling it from async
handlers blocks the event loop or requires thread offloading.

**Decision:** `aioboto3` against the S3-compatible endpoint. Presigning is
CPU-cheap and native; the same code works against real S3 later.

**Consequences:** Some MinIO-specific admin APIs are unavailable (not needed in
MVP). Bucket creation moves to a compose init sidecar.

**Status:** Accepted.

---

## ADR-009 — Redis is cache, not truth

**Context:** The source doc lists sessions, token blacklisting, rate limiting, and
caching in Redis without stating failure semantics.

**Decision:** Redis holds only reconstructible or ephemeral state. Auth fails
**open** on the blacklist (short token TTL bounds exposure); rate limiting fails
**closed to a conservative in-process limit**; tenant lookups fall back to
Postgres.

**Consequences:** A Redis outage degrades but does not corrupt. Documented
explicitly in the runbook and tested in the M5 chaos pass.

**Status:** Accepted.

---

## ADR-010 — Single error envelope (`problem+json`)

**Context:** The source doc has two incompatible shapes (`status/data/message` and
`detail`), which forces integrators to write two parsers.

**Decision:** One `application/problem+json` envelope with `code`, `detail`,
`trace_id`, `details[]`. Validation errors are normalised into `details[]`.

**Consequences:** Slightly more verbose success payloads; dramatically simpler
client error handling and log correlation.

**Status:** Accepted.

---

## ADR-011 — HTMX server-rendered console instead of an SPA

> **Superseded by ADR-016.** Kept for the reasoning trail.

**Context:** The product needs an admin UI for faskes staff and platform
operators. Options: Next.js SPA, Jinja2 + HTMX, or no UI.

**Decision:** Jinja2 templates + HTMX in a separate `frontend/` service, with
Redis-backed cookie sessions and CSRF protection, calling the JSON API over HTTP.

**Consequences:**
- Two deployables, but one origin via Caddy: no app/API CORS, one build pipeline,
  no token in browser storage.
- The API stays a pure JSON service, so it can be versioned, tested, and replaced
  independently of the console.
- The frontend is a real boundary: it cannot import backend code or touch the
  database, which keeps the HTTP contract honest.
- Auth is a session cookie, so the JSON API keeps bearer tokens and the console
  keeps a session — two auth paths, but both call the same permission layer.
- Interactivity is limited to partial swaps; that is sufficient for tables,
  forms, and upload progress.
- If a richer frontend is needed later, `/api/v1` is already there and the console
  can be replaced without touching domain code.

**Status:** Superseded by ADR-016.

---

## ADR-012 — Mock-first SATUSEHAT adapter (port & adapter)

**Context:** SATUSEHAT production access requires a registered PT, a faskes
record, and a Kemenkes onboarding agreement. The MVP cannot wait for that, and
should not hard-code FHIR calls into domain modules.

**Decision:** A `SatusehatPort` protocol with two implementations: `mock`
(deterministic, local, default) and `live` (real OAuth2 + FHIR R4). Selection is
configuration only (`SATUSEHAT_MODE`). No module outside
`modules/integrations/satusehat/` may import a FHIR client.

**Consequences:**
- The pipeline — credentials, token caching, outbox, retries, idempotency — is
  fully testable today.
- The mock cannot prove Kemenkes-specific validation, rate limits, or
  terminology requirements; `docs/satusehat.md` states this explicitly.
- Going live requires credentials and a smoke test, not a refactor.
- A contract test asserts both adapters satisfy the protocol shape.

**Status:** Accepted.

---

## ADR-013 — Per-tenant encrypted credentials with a separate key

**Context:** Each faskes has its own SATUSEHAT client credentials. Storing them
plaintext makes a database dump equivalent to an integration takeover.

**Decision:** Credentials live in the tenant schema; `client_secret` is encrypted
with Fernet using `APP_ENCRYPTION_KEY`, which is separate from `SECRET_KEY` and
never stored in the database. Secrets are write-only in API and app, and
never rendered, logged, or included in audit metadata.

**Consequences:**
- Rotating `APP_ENCRYPTION_KEY` requires a re-wrap migration; a CLI command and a
  tested drill exist (M7).
- Losing the key means re-entering every tenant's secret — documented, and the
  blast radius is bounded (no data loss).
- Database dumps contain ciphertext and are useless without the key; key and dump
  must be backed up separately.

**Status:** Accepted.

---

## ADR-014 — One tenant equals one faskes

**Context:** A tenant could represent either a single health facility or a legal
entity (PT) owning several facilities. The choice determines whether the schema
needs a facility hierarchy, whether credentials are per-facility or per-group,
and how RLS and provisioning work.

**Decision:** One tenant = one faskes. A group owning several facilities is
represented by several tenants that share an owner identity through multiple
`memberships`. No parent/child tenancy, no facility table.

**Consequences:**
- Provisioning stays one schema per facility; RLS and `SET LOCAL search_path`
  remain simple.
- A user who owns three clinics switches tenants in the app rather than
  seeing a rollup.
- Per-facility credentials match how SATUSEHAT onboarding actually works.
- Group-level reporting (if ever needed) becomes a read-only aggregate across
  tenants, not a new authorization path.
- Migration cost grows with facility count, which is the expected fleet size.

**Status:** Accepted.

---

## ADR-015 — Monorepo split: backend API + frontend BFF

**Context:** The project needs a UI, and the repository should separate backend
and frontend. HTMX was already chosen, which is normally server-rendered inside
the API process.

**Decision:** Two deployable services in one repository:

- `backend/` — pure JSON API, worker, migrations, integration adapter. No HTML,
  no templates, no session cookies.
- `frontend/` — a Next.js app acting as a Backend-For-Frontend. Holds the cookie
  session and calls `/api/v1` over HTTP. No database driver, no imports from
  `backend/`.

Both sit behind Caddy on one origin (`/` → frontend, `/api` → backend), so the
app/API path needs no CORS; the storage bucket has its own allowlist for direct
uploads.

**Consequences:**
- One extra container and ~0.5–1 day of work (session bridge, API client,
  error mapping).
- The API remains a clean, independently testable contract; the app is
  replaceable without touching domain code.
- Tokens stay server-side: the browser only ever holds an opaque session id.
- Versioning discipline is required — an API change can break the UI, so contract
  tests and OpenAPI diffs run in CI.
- Two images to build; the screenshot harness targets the proxy, not a port, so
  paths match production.

**Rejected:** templates inside the API (weak boundary, mixes concerns); Next.js
SPA (more work, tokens in JS, contradicts the earlier HTMX decision).

**Status:** Amended by ADR-016.

---

## ADR-016 — Next.js single app replaces the HTMX console

**Context:** The product needs a public marketing site comparable to dhealth.co.id
(SEO, typography, trust signals, lead capture) alongside the authenticated app.
HTMX was chosen when the UI was an internal admin console only. A marketing site
built in HTMX would require hand-building every interaction and would still lose
on SEO tooling and design velocity.

**Decision:** One Next.js 15 App Router application in `frontend/`, covering
marketing, auth, faskes app, and `/ops`. Tailwind + shadcn/ui + Lucide. The
FastAPI backend remains a pure JSON API.

Route handlers and Server Components act as the BFF: tokens live in a Redis-backed
session and never reach client JavaScript.

**Consequences:**
- The project gains a Node build step, a second runtime, and ~1 day of extra work.
- ONE design system and ONE component library across marketing and app, which is
  the main reason to choose a single app over two stacks.
- Marketing pages can be static/ISR, so they stay fast and survive a backend outage.
- MinIO must allow CORS from the site origin for direct presigned uploads.
- ADR-011 and ADR-015 are superseded/amended; the BFF principle survives.
- The API contract is now load-bearing for two surfaces, so OpenAPI diffs run in CI.

**Rejected:** HTMX marketing site (weak SEO/design velocity); Astro + Next.js
(two frameworks); Next.js marketing + HTMX app (three runtimes, two design systems).

**Status:** Accepted.

---

## ADR-017 — Reset `simple-websocket` into this project

**Context:** The chosen repository, `Harisalghifary/simple-websocket`, contains 43
lines of Express + Socket.IO and three commits. It has no UI, tests, database, or
structure. It cannot serve as a technical foundation for this design.

**Decision:** Treat it as the **destination**, not the base. Rename the GitHub
repository to `sehat-bridge`, tag the existing state `legacy/socket-chat`, then
replace the working tree with the monorepo described here. Preserve history.

**Consequences:**
- The old demo stays recoverable from the tag and the commit history.
- No code is reused; the Socket.IO chat is a different product.
- The repository URL changes, so any old links break (accepted).
- If realtime chat returns later, it returns as a new service, not this demo.

**Status:** Accepted.

---

## Deferred decisions (explicitly not decided now)

| Topic | Trigger to revisit |
|---|---|
| Single-schema + RLS mode | Tenant count > 200, or migration time > 10 min |
| OAuth/SSO, MFA | First enterprise customer requirement |
| Event bus | Second service or async side-effect that must survive restarts |
| UUIDv7 | Measured index bloat from random UUID PKs |
| Sharding | Write throughput or dataset size exceeds a single primary |
| Health-domain entities | After v0.1.0 platform sign-off |
| Real SATUSEHAT production traffic | PT + faskes onboarding + Kemenkes agreement in place |

---
