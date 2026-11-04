# 04 — API Specification (v0.1.0)

Base: `/api/v1`. All responses JSON unless noted. All errors use the
`application/problem+json` envelope from `02-architecture.md §7.1`.

## 0. Conventions

- **Auth:** `Authorization: Bearer <access_token>` on everything except
  `register`, `login`, `refresh`, `/health/*`, `/metrics`.
- **Tenant:** `X-Tenant-ID: <slug>` optional. When present it MUST match the
  token's `tid`, else `403 tenant_mismatch`.
- **Idempotency:** `Idempotency-Key: <uuid4>` on POST/PATCH. Replay with the same
  key returns the original response; replay with a different body returns
  `422 idempotency_key_reuse`.
- **Pagination:** `limit` (1–100, default 50), `cursor`.
- **Timestamps:** RFC 3339 UTC. IDs are UUIDv4 strings in v0.1.0.

## 1. Health & ops

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health/live` | none | 200 always if the process is up |
| GET | `/health/ready` | none | 200 or 503; body lists postgres/redis/minio |
| GET | `/metrics` | internal token | Prometheus; not exposed publicly |

```json
// 503
{ "status": "unavailable",
  "checks": { "postgres": "ok", "redis": "fail", "minio": "ok" } }
```

## 2. Auth

### POST `/auth/register`

Registers a user into an existing tenant; creates the membership as `member`.

```json
{ "tenant_slug": "acme", "email": "a@b.co", "password": "min-12-chars", "display_name": "Ada" }
```
`201` →
```json
{ "user": { "id": "…", "email": "a@b.co", "role": "member" },
  "access_token": "eyJ…", "refresh_token": "…", "token_type": "bearer", "expires_in": 900 }
```
Errors: `409 email_in_use`, `404 tenant_not_found` (same body as a suspended
tenant to avoid enumeration), `422 weak_password`, `403 registration_disabled`.

### POST `/auth/login`

```json
{ "tenant_slug": "acme", "email": "a@b.co", "password": "…" }
```
`200` → same token payload as register.
`401 invalid_credentials` for wrong password, unknown email, wrong tenant, or
inactive user — one message, one timing profile.

### POST `/auth/refresh`

```json
{ "refresh_token": "…" }
```
`200` → new access + new refresh (rotation).
`401 invalid_refresh` when expired, revoked, unknown, or **reused**. Reuse
revokes the entire family and writes an `auth.refresh_reuse` audit row.

### POST `/auth/logout`

Auth required. Body optional `{ "all_sessions": true }`. Blacklists the current
`jti` for its remaining lifetime; `all_sessions` revokes the refresh family.
`204`.

### POST `/auth/verify-email` / `/auth/password-reset/*`

Reserved shapes, implemented in M5 against Mailpit:
`202 { "message": "If the address exists, a link was sent." }` — always 202.

## 3. Users & roles

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/users/me` | any member | user + membership + tenant |
| PATCH | `/users/me` | any member | display_name, timezone, avatar_file_id |
| GET | `/users` | admin+ | paginated memberships of current tenant |
| PATCH | `/users/{user_id}/role` | owner/admin | `{ "role": "admin" }` |

Role rules (enforced in service, tested):
- `member` may never grant roles.
- `admin` may promote/demote `member` and `admin`, never `owner`.
- At least one `owner` must remain; demoting the last owner returns
  `409 last_owner`.
- Cross-tenant `user_id` returns `404`, not `403`, to avoid existence leaks.

```json
// GET /users/me
{ "id": "…", "email": "a@b.co", "is_verified": false,
  "is_platform_admin": false,
  "membership": { "role": "owner", "tenant": { "id": "…", "slug": "acme", "name": "Acme" } },
  "profile": { "display_name": "Ada", "timezone": "UTC", "avatar_file_id": null } }
```

## 4. Files

Limits (config, defaults): `MAX_FILE_BYTES=25MB`, allowlist
`image/png, image/jpeg, application/pdf, text/plain, text/csv`, per-tenant quota
`QUOTA_BYTES=1GB`.

### POST `/files/presign-upload`

```json
{ "filename": "report.pdf", "content_type": "application/pdf", "size_bytes": 1048576 }
```
`200` →
```json
{ "file_id": "…",
  "upload": { "url": "http://localhost:9000/seha-files",
              "fields": { "key": "tenants/…/…", "policy": "…", "x-amz-signature": "…",
                          "Content-Type": "application/pdf" },
              "method": "POST", "expires_in": 600 },
  "max_size_bytes": 26214400 }
```
The POST policy carries `content-length-range` and a `Content-Type` condition, so
MinIO rejects oversize or mislabelled bodies before they land.
Errors: `413 file_too_large`, `415 unsupported_media_type`, `409 quota_exceeded`,
`503 storage_unavailable`.

The POST policy pins `content-length-range` to the reserved size and an exact
`Content-Type`, so MinIO rejects oversize or mislabelled bodies before they land.

### POST `/files/{file_id}/complete`

`200` → file object. Performs `HEAD`, verifies `Content-Length` and
`Content-Type`, stores SHA-256, `status` → `ready`.
Errors: `404 object_not_found`, `409 already_completed`, `409 size_mismatch`,
`409 content_type_mismatch`, `410 upload_expired`.

### GET `/files/{file_id}/download`

`200` → `{ "url": "…", "expires_in": 300 }`. Presigned GET, no body stream
through the app.

### GET `/files`

Cursor paginated, newest first: `{ "items": [...], "next_cursor": "…", "has_more": true }`.
Optional `status`, `owner` (admin only). Members see only their own files; deleted
rows are hidden unless `status=deleted` is requested.

### DELETE `/files/{file_id}`

`204`. Marks deleted, removes the object, writes audit. Idempotent.

## 5. Platform admin

A platform admin is a user with `is_platform_admin = true` and **no tenant
membership**. Ops access uses the same password auth but a tenant-less token.

### POST `/auth/platform-login`

```json
{ "email": "ops@example.com", "password": "…" }
```
`200` → access + refresh token with `tid: null`, `scope: "platform"`.
`401 invalid_credentials` otherwise. Rate limited like normal login.

The `/ops/masuk` page uses this. The static `PLATFORM_ADMIN_TOKEN` from the
environment remains CLI-only (bootstrap and recovery) and is never accepted from
a browser request.

| Method | Path | Notes |
|---|---|---|
| GET | `/users/me` | operator identity when called with a platform token; membership is `null` |
| POST | `/admin/tenants` | `{ "slug": "faskes-x", "name": "…", "owner_email": "…", "password": "…" }` → 201 with provisioning steps |
| GET | `/admin/tenants` | list with status and member counts |
| GET | `/admin/tenants/{slug}` | detail plus active and failed job counts |
| POST | `/admin/tenants/{slug}/suspend` / `/resume` | idempotent operator action, audited |
| GET | `/admin/audit` | filters `tenant`, `action`, `created_from`, `created_to`; cursor-free `limit`/`offset` |
| GET | `/admin/audit/actions` | distinct actions for the filter dropdown |
| GET | `/admin/health` | dependencies, version, uptime, tenant counts, queue depth |

Tenant creation is also available as `make tenant`, which calls the same service
so the two paths cannot diverge.

## 6. Status code contract

| Code | Used for |
|---|---|
| 200 / 201 / 204 | success |
| 400 | malformed body |
| 401 | missing/expired/blacklisted token, bad credentials |
| 403 | wrong tenant, insufficient role, suspended tenant |
| 404 | unknown resource **or** resource in another tenant (no existence leak) |
| 409 | conflict (email in use, last owner, quota, state transition) |
| 410 | expired upload |
| 413 / 415 | size / media type |
| 422 | validation and idempotency-body mismatch |
| 429 | rate limited; `Retry-After` set |
| 503 | dependency unavailable |

## 7. Rate limits (defaults)

| Scope | Limit |
|---|---|
| `login` per email+tenant | 5 / 5 min, then backoff |
| `register` per IP | 10 / hour |
| `refresh` per user | 30 / hour |
| authenticated per tenant | 600 / min |
| `presign-upload` per tenant | 60 / min |

Exceeded → `429` with `Retry-After`, and a `rate_limit.exceeded` audit row
(sampled, to avoid log flooding).

## 8. OpenAPI requirements

Every endpoint ships: summary, description, request/response examples, all error
codes, and auth documented as a bearer scheme. `make docs` serves Swagger at
`/docs` and ReDoc at `/redoc`. A CI test asserts every declared error code is
produced by at least one test.
## 9. SATUSEHAT integration

All of these are per-tenant and require `admin` or `owner`. They talk to the
configured adapter (`mock` by default).

### GET `/integrations/satusehat`

`200` →
```json
{ "provider": "satusehat", "status": "unverified",
  "has_secret": true, "organization_id": "1000000001",
  "base_url": "http://mock-satusehat:8080/fhir-r4/v1",
  "last_verified_at": null, "last_error": null,
  "mode": "mock" }
```
The secret is never returned in any form. `404 credentials_not_found` when the
tenant has not configured the provider.

### PUT `/integrations/satusehat`

```json
{ "client_id": "…", "client_secret": "…", "organization_id": "…" }
```
`200` → same shape as GET, `status` reset to `unverified`.
`422 invalid_credentials_shape` if `client_id` or `organization_id` are empty.
Rotating the secret requires re-running test-connection before sync is allowed.

### POST `/integrations/satusehat/test`

Performs a token request and a `GET /Organization/{id}`. `200` →
`{ "status": "connected", "latency_ms": 12 }`; on failure `200` with
`{ "status": "error", "error": "..." }` (a failed test is a successful report,
not an HTTP error).

### POST `/integrations/satusehat/sync`

```json
{ "kind": "organization" }
```
`202` → `{ "job_id": "…", "status": "queued" }`.
`409 credentials_not_verified`, `409 sync_already_queued`.

### GET `/integrations/satusehat/jobs`

Cursor paginated history: `{ items: [{ id, kind, status, attempts, last_error,
created_at, updated_at }], next_cursor, has_more }`.

### GET `/integrations/satusehat/jobs/{job_id}`

Single job with `response_body` (identifier-redacted) and the current
`fhir_id` mapping. `404 job_not_found` for an unknown or cross-tenant job.

### Contract with the web app

The Next.js app calls these endpoints over HTTP; tests exercise the same service
layer through the API. There is one implementation, two consumers.

## 10. Web routes (HTML)

Served by the **Next.js frontend**, not by the API. They live under `/app` and
`/ops` (plus the public marketing routes), use cookie sessions rather than bearer
tokens, and are excluded from
the JSON OpenAPI schema. The Next.js route handlers serve full pages, streamed
server components, or `303` redirects — never JSON from a page route.

The frontend calls the endpoints in this document over HTTP; it has no database
access. Behaviour, screens, and styling: `08-ui.md`.

## 11. Versioning policy

- Path versioning `/api/v1`. Breaking changes require `/api/v2`; additive
  fields are allowed within v1.
- Deprecation: `Deprecation` and `Sunset` headers, minimum 90 days.
- The web app is not versioned; it ships as its own image.

## 12. Public marketing endpoints

### POST `/leads`

No auth. Called by the Next.js route handler, never directly by the browser.

```json
{ "name": "dr. Sari", "email": "sari@example.com",
  "facility_name": "Klinik Sehat Bersama", "facility_type": "klinik",
  "city": "Bandung", "phone": "0812…",
  "message": "Ingin melihat alur integrasi SATUSEHAT",
  "website": "", "elapsed_ms": 8420 }
```

`202` → `{ "message": "Terima kasih, tim kami akan menghubungi Anda." }`

Anti-abuse, all server-side:
- `website` is a honeypot: non-empty → return `202` without persisting (do not
  tell the bot).
- `elapsed_ms < 3000` → `202` without persisting.
- Rate limit per IP (5/hour) and globally (100/hour) → `429`.
- Duplicate email + facility within 24 h updates the existing lead instead of
  creating a second row.

Errors never reveal whether an email already exists.

### GET `/public/health`

Unauthenticated, minimal: `{ "status": "ok", "version": "0.1.0" }`.
Used by the marketing site's status pill. No dependency details (those stay on
`/health/ready`, internal only).

## 13. Rate limit additions

| Scope | Limit |
|---|---|
| `POST /leads` per IP | 5 / hour |
| `POST /leads` global | 100 / hour |
| `POST /auth/platform-login` per email | 5 / 5 min |
