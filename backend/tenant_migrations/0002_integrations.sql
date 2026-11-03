-- 0002_integrations — SATUSEHAT credentials and the sync outbox.
-- Forward-only and re-runnable.

DO $$ BEGIN
    CREATE TYPE sync_kind AS ENUM ('organization', 'patient');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE sync_status AS ENUM ('queued', 'running', 'done', 'failed', 'dead');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS integration_credentials (
    provider           text PRIMARY KEY CHECK (provider IN ('satusehat')),
    client_id          text NOT NULL,
    client_secret_enc  bytea NOT NULL,
    organization_id    text,
    base_url           text NOT NULL,
    status             text NOT NULL DEFAULT 'unverified'
                       CHECK (status IN ('unverified', 'connected', 'error')),
    last_error         text,
    last_verified_at   timestamptz,
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sync_jobs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL,
    kind            sync_kind NOT NULL,
    local_id        uuid NOT NULL,
    payload         jsonb NOT NULL,
    status          sync_status NOT NULL DEFAULT 'queued',
    attempts        int NOT NULL DEFAULT 0,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    last_error      text,
    response_body   jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- History is unbounded; only active jobs are unique per resource.
CREATE UNIQUE INDEX IF NOT EXISTS sync_jobs_active_key
    ON sync_jobs (kind, local_id)
    WHERE status IN ('queued', 'running');

CREATE INDEX IF NOT EXISTS sync_jobs_ready_idx
    ON sync_jobs (next_attempt_at)
    WHERE status IN ('queued', 'running');
CREATE INDEX IF NOT EXISTS sync_jobs_tenant_time_idx
    ON sync_jobs (tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS sync_resources (
    kind       sync_kind NOT NULL,
    local_id   uuid NOT NULL,
    fhir_id    text NOT NULL,
    fhir_type  text NOT NULL,
    synced_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (kind, local_id)
);

ALTER TABLE integration_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_credentials FORCE  ROW LEVEL SECURITY;
ALTER TABLE sync_jobs               ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_jobs               FORCE  ROW LEVEL SECURITY;
ALTER TABLE sync_resources          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_resources          FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY integration_credentials_tenant_isolation
        ON integration_credentials
        USING (current_setting('app.tenant_id', true) <> '');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY sync_jobs_tenant_isolation
        ON sync_jobs
        USING (tenant_id::text = current_setting('app.tenant_id', true));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY sync_resources_tenant_isolation
        ON sync_resources
        USING (current_setting('app.tenant_id', true) <> '');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;