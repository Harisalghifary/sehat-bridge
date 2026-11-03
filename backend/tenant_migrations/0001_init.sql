-- 0001_init — the first schema every tenant receives.
-- Applied by app.tenancy.service inside a transaction with search_path set to
-- the tenant schema. Must stay forward-only and re-runnable.

DO $$ BEGIN
    CREATE TYPE file_status AS ENUM ('uploading', 'ready', 'deleted');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS profiles (
    user_id        uuid PRIMARY KEY,
    display_name   text NOT NULL,
    avatar_file_id uuid,
    timezone       text NOT NULL DEFAULT 'UTC',
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS files (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid NOT NULL,
    owner_user_id  uuid NOT NULL,
    object_key     text NOT NULL UNIQUE,
    filename       text NOT NULL,
    content_type   text NOT NULL,
    size_bytes     bigint NOT NULL CHECK (size_bytes > 0),
    sha256         bytea,
    status         file_status NOT NULL DEFAULT 'uploading',
    created_at     timestamptz NOT NULL DEFAULT now(),
    completed_at   timestamptz,
    deleted_at     timestamptz
);

CREATE INDEX IF NOT EXISTS files_owner_time_idx
    ON files (owner_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS files_expiry_idx
    ON files (created_at) WHERE status = 'uploading';

CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

-- Schema isolation is primary; RLS is the second line of defence.
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE files FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY profiles_tenant_isolation ON profiles
        USING (
            user_id IS NOT NULL
            AND current_setting('app.tenant_id', true) <> ''
        );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY files_tenant_isolation ON files
        USING (tenant_id::text = current_setting('app.tenant_id', true));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;