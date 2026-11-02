# 06 — Testing, CI, Observability & Operations

## 1. Test strategy

Three layers, all runnable locally with Docker. Integration tests use
Testcontainers so CI and laptop behaviour match.

| Layer | Scope | Tooling | Budget |
|---|---|---|---|
| Unit | security, tokens, pagination cursors, error mapping, slug validation | pytest | < 5 s |
| Integration | real Postgres + Redis + MinIO containers, HTTP via `httpx.AsyncClient` | pytest-asyncio, testcontainers | < 120 s |
| Contract | every documented error code and status is produced by a test | pytest + OpenAPI parse | < 10 s |

No mocks for Postgres or MinIO. Mocks hide the exact class of bug this design is
most exposed to.

## 2. Required test matrix

### 2.1 Tenancy (highest value — treat as P0)

| ID | Scenario | Expected |
|---|---|---|
| T-01 | Request as tenant A, `X-Tenant-ID: B` | 403 `tenant_mismatch` |
| T-02 | Token with `tid=A`, reads files | only A's rows |
| T-03 | 50 interleaved A/B requests on a 2-conn pool | zero bleed, same as serial |
| T-04 | Query tenant table without `app.tenant_id` set | RLS returns zero rows |
| T-05 | Cross-tenant `file_id` / `user_id` | 404, no URL issued |
| T-06 | Provision, fail midway, retry | no duplicate schema, final state `active` |
| T-07 | `search_path` after a request finishes | restored (assert via `current_setting`) |
| T-08 | Migration fan-out over 3 tenants with one failure | 2 succeed, 1 marked failed, exit ≠ 0 |

### 2.2 Auth

- register → login → refresh → old refresh reuse revokes family
- expired access token, wrong `aud`, wrong `iss`, tampered signature, `alg: none`
- blacklisted `jti` rejected before natural expiry
- login timing parity for unknown email vs wrong password (±20%)
- password reset token single-use and expiry-bound
- suspended tenant cannot authenticate

### 2.3 Files

- policy rejects oversize and wrong MIME server-side
- `complete` verifies size/type; mismatch → 409
- expired upload released from quota by sweeper
- delete removes the object and is idempotent
- presigned URL expires

### 2.4 Contracts

- every error code in `04-api-spec.md §6` appears in a test
- every endpoint rejects missing auth (except the documented public ones)
- pagination cursor tampering → 422, not 500

## 3. CI pipeline

```
backend-lint    ruff check + ruff format --check
backend-types   mypy app/
unit            pytest -m "not integration"
integ           pytest -m integration          (service containers)
contract        pytest -m contract
drift           provision fresh tenant → compare to seeded tenant
guard           grep checks: no session-level SET search_path, no module-level DB client
coverage        fail under 80% for app/core and app/modules

frontend-lint   eslint + tsc --noEmit
frontend-build  next build (standalone)
e2e             Playwright: marketing page, login, upload, permission denial
a11y            axe on /, /solusi, /demo, /app/dasbor
lighthouse      mobile budgets on /, /solusi, /demo
copy            fail on lorem ipsum, TODO, unlabelled numeric claims
```

Target: full pipeline under 8 minutes. Failing `drift`, `guard`, `lighthouse`,
or `copy` blocks merge regardless of coverage. Lighthouse runs on a built image,
not `next dev`.

## 4. Observability

### 4.1 Logging (structlog, JSON in prod, pretty in dev)

Every request line includes: `request_id`, `method`, `route`, `status`,
`latency_ms`, `tenant_slug`, `user_id` (or `anon`), `client_ip`.

Never logged: tokens, passwords, presigned URLs, `PLATFORM_ADMIN_TOKEN`,
Authorization headers. A scrubber runs on the log processor chain so an
accidental `logger.info(..., headers=...)` cannot leak.

### 4.2 Metrics

- `http_request_duration_seconds{route,status}` histogram
- `auth_login_total{result}`
- `tenant_provision_duration_seconds`, `tenant_provision_failures_total`
- `file_upload_bytes_total{tenant}`, `file_quota_rejections_total`
- `db_pool_in_use`, `db_pool_wait_seconds`
- `redis_command_duration_seconds`, `s3_request_duration_seconds`

Cardinality guard: `tenant` label is capped to top-N plus `other`.

### 4.3 Traces

One span per request; child spans for DB transaction, Redis call, S3 presign.
`tenant_slug` and `user_id` as span attributes (not labels).

## 5. Runbook (summary; full version in `docs/runbook.md`)

| Symptom | First check | Action |
|---|---|---|
| 5xx spike, DB ok | connection pool saturation (`db_pool_in_use`) | raise pool / find long transaction |
| Requests slow only for one tenant | audit + query timing for that slug | check tenant table bloat, run `VACUUM ANALYZE` |
| `tenant_mismatch` spike | client integration bug vs attack | inspect IPs, consider blocking |
| Login works, data 404s | `search_path` restore failure | restart workers, run T-07 |
| Migration stalled | `tenant_migrations` vs `schema_migrations` | resume fan-out, never hand-edit |
| MinIO 503 only in prod | `MINIO_PUBLIC_URL` vs endpoint | presigned URLs signed for wrong host |
| Redis down | expected degradation | auth blacklist fails open, rate limit falls back in-process |

### Backup / restore

- Nightly: `pg_dump` of `public` + one `pg_dump -n tenant_<slug>` per tenant.
- Restore drill is a milestone acceptance item (M5), not a someday task.
- MinIO: versioning on the bucket; object keys are derivable from `files` rows, so
  metadata restore precedes blob restore.

## 6. Security checklist (pre-release)

- [ ] CORS allowlist explicit, no `*` with credentials
- [ ] Security headers (`HSTS`, `X-Content-Type-Options`, `Referrer-Policy`)
- [ ] Trusted host middleware configured for prod
- [ ] Rate limits active on auth routes
- [ ] `SECRET_KEY` and DB credentials from env/secret store, never in images
- [ ] Non-superuser DB role; RLS `FORCE` verified by test
- [ ] Presigned URLs short-lived; bucket not public
- [ ] Dependencies pinned via `uv.lock`; `pip-audit` in CI (non-blocking advisory)
- [ ] No debug endpoints reachable when `ENV=prod`
- [ ] Log scrubber test passes (no token material in captured logs)

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cross-tenant leak via pooled connection | Med | Critical | `SET LOCAL` only, T-03/T-04/T-07, CI grep guard |
| Header-spoofed tenant | High if copied from source doc | Critical | JWT `tid` authoritative, T-01 |
| Migration drift across schemas | Med | High | forward-only files + CI drift test |
| Refresh-token reuse undetected | Med | High | family revocation + audit + test |
| MinIO presign host mismatch | High in dev | Med | separate public URL from day one |
| Scope creep into health domain | High | Med | M6 explicitly excludes it; new ADR required |
| RLS assumed but not applied | Med | High | `FORCE RLS` + non-owner role + T-04 |
## 8. Frontend testing (Next.js + marketing)

| ID | Scenario | Expected |
|---|---|---|
| U-01 | Login with bad password | inline form error, no session, uniform copy |
| U-02 | Mutating route handler without matching `Origin` | 403, no state change |
| U-03 | Tenant member opens `/ops/tenant` | 403 page, no nav entry |
| U-04 | Upload 26 MB via the app | storage rejection surfaced, no orphan row |
| U-05 | Admin demotes the owner | inline error, select reverts |
| U-06 | Marketing pages with JS disabled | all content and links present |
| U-07 | Presigned URL or token in rendered HTML/JS | grep test fails if present |
| U-08 | Session expiry mid-form | redirect to `/masuk?next=…`, message shown |
| U-09 | axe/pa11y on `/`, `/solusi`, `/demo`, `/app/dasbor` | no violations |
| U-10 | Playwright: happy path, permission denial, lead form | pass in CI |
| U-11 | Lighthouse CI on `/`, `/solusi`, `/demo` (mobile) | Perf ≥ 90, A11y ≥ 95, SEO 100 |
| U-12 | Demo form: honeypot, fast submit, 6th submission | 202 without row ×2, then 429 |
| U-13 | `sitemap.xml`, `robots.txt`, OG image, JSON-LD | present and valid |
| U-14 | Backend stopped | marketing still serves; `/app` shows retry boundary |
| U-15 | Keyboard-only pass | focus order, drawer trap, skip link |

Component tests are not written for styling. Marketing copy is checked by a lint
rule that fails on lorem ipsum, "TODO", or unlabelled numeric claims.

## 9. Adapter testing

- **Contract:** both `mock` and `live` satisfy `SatusehatPort` (mypy protocol
  check + runtime `inspect.signature` assertions).
- **Determinism:** same input → same `fhir_id` from the mock, across processes.
- **Failure injection:** `?fail=500`, `?fail=timeout`, `?fail=4xx` drive retry vs
  terminal-failure paths.
- **Idempotency:** sync twice → one job, one mapping, same `fhir_id`.
- **Secret hygiene:** captured logs, audit metadata, and API responses are scanned
  for the literal test secret.
- **Live smoke:** opt-in, skipped unless `SATUSEHAT_TEST_*` env vars are present.

## 10. Additional risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Mock drifts from real SATUSEHAT behaviour | High | Med | mock follows published FHIR R4 shapes; `docs/satusehat.md` lists what is unproven; live smoke test when credentials exist |
| Team treats mock as "integration done" | Med | High | success criteria require an explicit "unproven in production" section in docs |
| Session cookie auth bypasses role checks | Low | High | the app uses the same API permission checks; U-03 test |
| Secret leaks into template or log | Med | Critical | write-only secret model, grep tests, log scrubber |
| Marketing copy drifts into unverifiable claims | Medium | High | `copy` CI check + explicit banned-claims list in ADR-016 |
| Server Component leaks the access token to the client | Low | Critical | tokens confined to server session; grep + U-07 |
