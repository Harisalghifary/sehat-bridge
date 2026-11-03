"""Public schema baseline.

Revision ID: 0001_public
Revises:
Create Date: 2026-11-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.config import get_settings

revision: str = "0001_public"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = [
    "tenants",
    "users",
    "memberships",
    "refresh_tokens",
    "leads",
]


def _grant_app_role() -> None:
    role = get_settings().app_db_role
    exists = (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role})
        .scalar()
    )
    if not exists:
        return

    op.execute(f'GRANT USAGE ON SCHEMA public TO "{role}"')
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {", ".join(TABLES)} TO "{role}"')
    op.execute(f'GRANT SELECT, INSERT ON audit_log TO "{role}"')
    op.execute(f'GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO "{role}"')


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE tenant_status AS ENUM
                ('provisioning', 'active', 'suspended', 'failed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            slug         citext NOT NULL UNIQUE,
            name         text   NOT NULL,
            status       tenant_status NOT NULL DEFAULT 'provisioning',
            plan         text   NOT NULL DEFAULT 'free',
            failure_note text,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT slug_format CHECK (slug ~ '^[a-z0-9][a-z0-9_-]{1,62}$')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email             citext NOT NULL UNIQUE,
            hashed_password   text NOT NULL,
            is_active         boolean NOT NULL DEFAULT true,
            is_verified       boolean NOT NULL DEFAULT false,
            is_platform_admin boolean NOT NULL DEFAULT false,
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE member_role AS ENUM ('owner', 'admin', 'member');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memberships (
            user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tenant_id  uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            role       member_role NOT NULL DEFAULT 'member',
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, tenant_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS memberships_tenant_role_idx ON memberships (tenant_id, role)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            token_hash  bytea NOT NULL UNIQUE,
            family_id   uuid NOT NULL,
            expires_at  timestamptz NOT NULL,
            revoked_at  timestamptz,
            replaced_by uuid REFERENCES refresh_tokens(id),
            user_agent  text,
            created_at  timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS refresh_tokens_family_idx ON refresh_tokens (family_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS refresh_tokens_expiry_idx "
        "ON refresh_tokens (expires_at) WHERE revoked_at IS NULL"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id            bigserial PRIMARY KEY,
            tenant_id     uuid REFERENCES tenants(id) ON DELETE SET NULL,
            actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
            action        text NOT NULL,
            resource_type text,
            resource_id   text,
            metadata      jsonb NOT NULL DEFAULT '{}',
            ip            inet,
            created_at    timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS audit_log_tenant_time_idx "
        "ON audit_log (tenant_id, created_at DESC)"
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE lead_status AS ENUM
                ('new', 'contacted', 'qualified', 'closed', 'spam');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name          text NOT NULL,
            email         citext NOT NULL,
            facility_name text NOT NULL,
            facility_type text,
            city          text,
            phone         text,
            message       text,
            source        text NOT NULL DEFAULT 'website',
            status        lead_status NOT NULL DEFAULT 'new',
            ip            inet,
            user_agent    text,
            created_at    timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS leads_time_idx ON leads (created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS leads_status_idx ON leads (status, created_at DESC)")

    _grant_app_role()


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS leads")
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
    op.execute("DROP TABLE IF EXISTS memberships")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS tenants")
    op.execute("DROP TYPE IF EXISTS lead_status")
    op.execute("DROP TYPE IF EXISTS member_role")
    op.execute("DROP TYPE IF EXISTS tenant_status")
