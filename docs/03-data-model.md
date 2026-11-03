# 03 — Data Model

Two namespaces: `public` (shared, Alembic-managed) and `tenant_<slug>`
(per-tenant, replayed from `tenant_migrations/`).

## 1. `public` schema

```sql
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

CREATE TYPE tenant_status AS ENUM ('provisioning','active','suspended','failed');

CREATE TABLE tenants (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug         citext NOT NULL UNIQUE,
  name         text   NOT NULL,
  status       tenant_status NOT NULL DEFAULT 'provisioning',
  plan         text   NOT NULL DEFAULT 'free',
  failure_note text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT slug_format CHECK (slug ~ '^[a-z0-9][a-z0-9_-]{1,62}$')
);

CREATE TABLE users (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email           citext NOT NULL UNIQUE,
  hashed_password text NOT NULL,
  is_active       boolean NOT NULL DEFAULT true,
  is_verified     boolean NOT NULL DEFAULT false,
  is_platform_admin boolean NOT NULL DEFAULT false,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TYPE member_role AS ENUM ('owner','admin','member');

CREATE TABLE memberships (
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tenant_id  uuid REFERENCES tenants(id) ON DELETE CASCADE,  -- null for platform tokens
  role       member_role NOT NULL DEFAULT 'member',
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, tenant_id)
);
CREATE INDEX memberships_tenant_role_idx ON memberships (tenant_id, role);

CREATE TABLE refresh_tokens (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tenant_id    uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  token_hash   bytea NOT NULL UNIQUE,          -- sha256(token)
  family_id    uuid NOT NULL,                  -- rotation chain
  expires_at   timestamptz NOT NULL,
  revoked_at   timestamptz,
  replaced_by  uuid REFERENCES refresh_tokens(id),
  user_agent   text,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX refresh_tokens_family_idx ON refresh_tokens (family_id);
CREATE INDEX refresh_tokens_expiry_idx ON refresh_tokens (expires_at) WHERE revoked_at IS NULL;

CREATE TABLE audit_log (
  id            bigserial PRIMARY KEY,
  tenant_id     uuid REFERENCES tenants(id) ON DELETE SET NULL,
  actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  action        text NOT NULL,           -- e.g. 'file.uploaded', 'auth.login_failed'
  resource_type text,
  resource_id   text,
  metadata      jsonb NOT NULL DEFAULT '{}',
  ip            inet,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_log_tenant_time_idx ON audit_log (tenant_id, created_at DESC);
-- appended by the app role only; no UPDATE/DELETE grant
```

Notes:
- Email is globally unique: one identity can belong to several tenants through
  `memberships`. This fixes the source document's `users.tenant_id` design, where
  an email could never exist in two tenants.
- Refresh tokens are stored **hashed**; a DB dump does not hand out sessions.
- `audit_log` is append-only by grant, not by convention.

## 2. Tenant schema (applied to every `tenant_<slug>`)

```sql
CREATE TABLE profiles (
  user_id        uuid PRIMARY KEY,           -- logical ref to public.users
  display_name   text NOT NULL,
  avatar_file_id uuid,
  timezone       text NOT NULL DEFAULT 'UTC',
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TYPE file_status AS ENUM ('uploading','ready','deleted');

CREATE TABLE files (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL,              -- denormalised for RLS defence
  owner_user_id  uuid NOT NULL,
  object_key     text NOT NULL UNIQUE,       -- tenants/{tenant_id}/{file_id}/{name}
  filename       text NOT NULL,
  content_type   text NOT NULL,
  size_bytes     bigint NOT NULL CHECK (size_bytes > 0),
  sha256         bytea,
  status         file_status NOT NULL DEFAULT 'uploading',
  created_at     timestamptz NOT NULL DEFAULT now(),
  completed_at   timestamptz,
  deleted_at     timestamptz
);
CREATE INDEX files_owner_time_idx ON files (owner_user_id, created_at DESC);
CREATE INDEX files_expiry_idx ON files (created_at) WHERE status = 'uploading';

CREATE TABLE schema_migrations (
  version    text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);

-- Defence in depth: schema isolation is primary, RLS catches mistakes.
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles FORCE  ROW LEVEL SECURITY;
ALTER TABLE files    ENABLE ROW LEVEL SECURITY;
ALTER TABLE files    FORCE  ROW LEVEL SECURITY;

CREATE POLICY profiles_tenant_isolation ON profiles
  USING (user_id IS NOT NULL AND current_setting('app.tenant_id', true) <> '');
CREATE POLICY files_tenant_isolation ON files
  USING (tenant_id::text = current_setting('app.tenant_id', true));
```

`FORCE ROW LEVEL SECURITY` matters: without it the table owner (our migration
role) bypasses policies entirely and the protection is theatre. The app connects
as a role that is **not** the schema/table owner, so policies actually apply.

No cross-schema foreign keys. `profiles.user_id` and `files.owner_user_id` are
logical references validated in the service layer; enforcing them would create a
dependency from tenant schemas into `public` that complicates per-tenant restores.

## 3. Indexing rationale

| Index | Query it serves |
|---|---|
| `memberships(tenant_id, role)` | member list, owner count, role checks |
| `refresh_tokens(family_id)` | reuse detection revokes a whole chain |
| `refresh_tokens(expires_at) WHERE revoked_at IS NULL` | cleanup sweeper |
| `files(owner_user_id, created_at DESC)` | “my files”, newest first |
| `files(created_at) WHERE status='uploading'` | expired-upload sweeper |
| `audit_log(tenant_id, created_at DESC)` | admin audit view |

## 4. Soft delete policy

`files.status='deleted'` + `deleted_at`, object removed from MinIO immediately
on delete (presigned URLs are short-lived, so dangling access is not a risk), row
retained 30 days for audit, then purged by a scheduled job. Users and tenants are
hard-deleted only through an operator command that also drops the schema.

## 5. Migration strategy

**Two ladders, on purpose.**

1. `public` — Alembic, single schema, normal `alembic upgrade head`.
2. `tenant_*` — plain versioned SQL files in `tenant_migrations/`,
   `0001_init.sql`, `0002_....sql`, applied per tenant. Alembic is **not** used
   here: running its version-table machinery across N dynamic schemas is fragile
   and drifts silently.

Each file must be:
- idempotent (`IF NOT EXISTS`, or guarded by the version table),
- forward-only (a paired `_down.sql` is required for the two most recent
  versions; older ones are forward-fix only),
- applied inside one transaction per schema.

**Drift test (CI):** provision a fresh tenant from scratch, then compare
`information_schema.columns` for every table against an existing seeded tenant
(column name, type, nullability, default). Any difference fails the build. This
is the only defence against hand-edited schemas.

**Ceiling:** fan-out is O(tenants). At ~200 tenants a full migration starts
hurting; the documented escape hatch is a single-schema + RLS mode, which is why
the repository layer keeps tenant filtering in one place (ADR-002).

## 6. Seed data (dev only)

`scripts/seed.py` creates:
- tenants `acme` and `globex` (plus `acme` re-run must be a no-op),
- owner + admin + member in `acme`, owner in `globex`,
- a shared email (`same@person.dev`) in **both** tenants, to prove memberships work,
- two sample files per tenant.

Print a ready-to-copy `.env.local` block with the demo credentials.
## 7. Integration tables (per tenant)

Added to `tenant_migrations/0002_integrations.sql`.

```sql
CREATE TABLE integration_credentials (
  provider             text PRIMARY KEY CHECK (provider IN ('satusehat')),
  client_id            text NOT NULL,
  client_secret_enc    bytea NOT NULL,          -- Fernet ciphertext
  organization_id      text,
  base_url             text NOT NULL,
  status               text NOT NULL DEFAULT 'unverified'
                       CHECK (status IN ('unverified','connected','error')),
  last_error           text,
  last_verified_at     timestamptz,
  updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TYPE sync_kind   AS ENUM ('organization','patient');
CREATE TYPE sync_status AS ENUM ('queued','running','done','failed','dead');

CREATE TABLE sync_jobs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL,
  kind           sync_kind NOT NULL,
  local_id       uuid NOT NULL,
  payload        jsonb NOT NULL,          -- snapshot at enqueue time
  status         sync_status NOT NULL DEFAULT 'queued',
  attempts       int NOT NULL DEFAULT 0,
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  last_error     text,
  response_body  jsonb,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (kind, local_id, status) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX sync_jobs_ready_idx ON sync_jobs (next_attempt_at)
  WHERE status IN ('queued','running');
CREATE INDEX sync_jobs_tenant_time_idx ON sync_jobs (tenant_id, created_at DESC);

CREATE TABLE sync_resources (
  kind         sync_kind NOT NULL,
  local_id     uuid NOT NULL,
  fhir_id      text NOT NULL,
  fhir_type    text NOT NULL,
  synced_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (kind, local_id)
);

ALTER TABLE integration_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_credentials FORCE  ROW LEVEL SECURITY;
ALTER TABLE sync_jobs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_jobs              FORCE  ROW LEVEL SECURITY;
ALTER TABLE sync_resources         ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_resources         FORCE  ROW LEVEL SECURITY;
```

Notes:
- `payload` is a **snapshot**, not a reference. If the local row changes after
  enqueue, the job still pushes what the user saw; a later job carries the newer
  state. This makes replay and audit honest.
- `UNIQUE (kind, local_id, status)` is intentionally *not* a uniqueness guarantee
  across all statuses — it prevents two queued jobs for the same resource while
  allowing history. The service additionally checks `sync_resources` before
  enqueue.
- Credentials live in the tenant schema, so dropping a tenant drops its secrets.
  The encryption key stays in the platform's environment, never in the database.
- Secret columns are excluded from `pg_dump`? **No** — dumps include ciphertext,
  which is why `APP_ENCRYPTION_KEY` must be backed up separately and never stored
  alongside dumps.

## 8. What the MVP deliberately does not store

- **No NIK, no patient names.** `PatientDraft` is built from a synthetic
  identifier in the mock flow. Storing real patient identifiers pulls UU PDP
  obligations (consent, retention, breach notification) that are out of scope
  until a real deployment exists.
- **No FHIR resource bodies** beyond `response_body` on failures, and that is
  redacted of identifiers before storage.

## 9. Marketing leads (`public` schema)

The site's only write path that does not require auth. Kept deliberately small.

```sql
CREATE TYPE lead_status AS ENUM ('new','contacted','qualified','closed','spam');

CREATE TABLE leads (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  email         citext NOT NULL,
  facility_name text NOT NULL,
  facility_type text,              -- klinik | rumah_sakit | lab | apotek | lainnya
  city          text,
  phone         text,
  message       text,
  source        text NOT NULL DEFAULT 'website',
  status        lead_status NOT NULL DEFAULT 'new',
  ip            inet,
  user_agent    text,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX leads_time_idx   ON leads (created_at DESC);
CREATE INDEX leads_status_idx ON leads (status, created_at DESC);
```

Rules:
- Validation at the edge: email format, required name/facility, message ≤ 2000
  chars; everything else optional.
- Anti-spam: honeypot field must be empty, submit timing < 3 s is rejected, and
  the route is rate limited per IP (5/hour) and globally (100/hour).
- `ip` and `user_agent` exist for abuse handling only, are never displayed in the
  app, and are purged after 90 days.
- Leads live in `public`, not a tenant schema: there is no tenant yet.
- Retention: 12 months, then deleted by a scheduled job. The privacy page states
  this in plain language.

## 10. Why no clinical tables in v0.1.0

Patients, encounters, prescriptions, and claims are intentionally absent. The
marketing site may show illustrative product imagery, but the authenticated app
must never display fabricated clinical data. Adding `patients` and
`appointments` is a documented next step, not an implicit part of this schema.
