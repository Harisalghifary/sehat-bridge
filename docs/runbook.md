# Runbook

Operational procedures for Sehat Bridge v0.1.0. Commands assume a Compose
deployment from the repository root.

## 1. First response

1. Check readiness: `make health` or `curl -fsS localhost:8080/api/v1/health/ready`.
2. Read one structured log line per request. It carries `request_id`,
   `method`, `status`, `latency_ms`, `tenant_slug`, and `user_id`.
3. Give the failing `X-Request-ID` / `trace_id` to the engineer; the same id is
   in the log line and every problem response.
4. Scrape metrics at `GET /api/v1/metrics` (add `Authorization: Bearer
   $METRICS_TOKEN` when the token is configured).

| Symptom | First check | Action |
|---|---|---|
| 5xx spike, DB ok | `db_pool_in_use` | find a long transaction; raise pool size only after the cause is fixed |
| Slow for one tenant | request latency by `tenant_slug`, table size | `VACUUM ANALYZE` that tenant schema |
| `tenant_mismatch` spike | client sends stale `X-Tenant-ID` | fix the client; treat repeated forged headers as an incident |
| Login works, data 404s | `search_path` restore | restart the API and re-run the tenancy test suite |
| Migration stalled | `tenant_migrations` vs `schema_migrations` | resume the fan-out; never hand-edit migration rows |
| Presigned upload 403 | `MINIO_PUBLIC_URL` host | re-sign for the browser-visible origin |
| Redis down | readiness `redis: error` | sessions fail closed, rate limits fail open; restart Redis |
| MinIO down | readiness `minio: error` | only uploads degrade; downloads and dashboard stay up |
| Mock SATUSEHAT down | worker job `last_error` | jobs retry with backoff, then `dead` at 5 attempts |

## 2. Rotate `SECRET_KEY`

`SECRET_KEY` signs JWTs. Rotating it invalidates every access and refresh token
and the two BFF session cookies; users sign in again.

```bash
# generate a new secret
python -c "import secrets; print(secrets.token_urlsafe(48))"
# edit .env, then recreate the API and frontend
docker compose up -d --no-deps backend frontend
make health
```

No database migration is needed. Refresh tokens are opaque and hashed in
Postgres, so they survive secret rotation but the access token that accompanies
them is rejected. Sign everyone in again by also revoking sessions when needed:

```bash
docker compose exec -T postgres psql -U sehat -d sehat \
  -c "UPDATE refresh_tokens SET revoked_at = now() WHERE revoked_at IS NULL;"
```

## 3. Re-wrap tenant secrets (`APP_ENCRYPTION_KEY`)

Integration `client_secret` values are Fernet-encrypted with a key derived from
`APP_ENCRYPTION_KEY`. Rotate in two steps: keep the old passphrase available,
set the new one, run the re-wrap job, then remove the old passphrase.

```bash
# 1. put the new key in .env as APP_ENCRYPTION_KEY (keep the old value handy)
# 2. recreate the API so the process reads the new key
docker compose up -d --no-deps backend
# 3. re-encrypt every tenant credential with the old key as the source
make rewrap-secrets OLD_KEY='the-previous-passphrase'
# 4. verify credentials still test successfully in /app/integrasi
```

The job decrypts every credential first and aborts before writing if any value
fails, so a partial rotation cannot brick half the tenants.

## 4. Restore one tenant schema

Nightly backups should include `public` plus one dump per tenant schema. The
drill proves a dump restores into a scratch schema with an identical column
shape without touching the live tenant.

```bash
make restore-drill TENANT=acme
# [ok] restore drill: tenant_acme restored and matched column-for-column
```

Manual restore into the live schema is a deliberate maintenance operation:

```bash
docker compose exec -T postgres pg_dump -U sehat -d sehat \
  --schema=tenant_acme --schema-only --no-owner > /tmp/tenant_acme.sql
# stop writers, drop the damaged schema, restore, run the drift test
```

Metadata restore precedes blob restore: object keys are derivable from `files`
rows, and a restored row may point at an object that still exists in MinIO.

## 5. Drain or replay a stuck sync job

The worker claims one job per tenant per cycle and recovers `running` jobs older
than `WORKER_STALE_SECONDS` automatically.

```bash
make worker-once                  # one pass across all active tenants
make worker                       # continuous worker

# Inspect a tenant's jobs
docker compose exec -T postgres psql -U sehat -d sehat -c \
  "SET search_path = tenant_acme, public;
   SELECT id, kind, status, attempts, next_attempt_at, last_error
     FROM sync_jobs ORDER BY created_at DESC LIMIT 20;"
```

To retry a `dead` job, put it back in the queue explicitly:

```sql
UPDATE sync_jobs
   SET status = 'queued', attempts = 0, next_attempt_at = now(),
       last_error = NULL, updated_at = now()
 WHERE id = '<job-uuid>';
```

Terminal 4xx failures (`failed`) are not retried automatically; fix credentials
or the payload and enqueue a new sync from `/app/integrasi`.

## 6. Retention

```bash
make retention
# retention: audit_rows=… leads=… tokens=…
```

Defaults: audit 365 days, leads 365 days, spent/expired auth tokens are removed
immediately. Schedule this daily with cron or an external scheduler; the command
is idempotent.

## 7. Chaos checks

| Failure | Expected behaviour |
|---|---|
| Redis stopped | readiness 503; login/session endpoints fail closed; rate limit fails open; marketing pages still serve |
| MinIO stopped | upload page shows a readable storage warning; other app pages work |
| Mock SATUSEHAT stopped | sync jobs retry with exponential backoff; no 5xx reaches the app |
| Backend stopped | marketing still serves from the frontend image; `/app` shows retry boundary |

Run the smoke and integration suite after every incident:

```bash
make smoke
make test
make test-integration
```