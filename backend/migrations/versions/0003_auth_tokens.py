"""Single-use email verification and password reset tokens.

Revision ID: 0003_auth_tokens
Revises: 0002_platform_refresh
Create Date: 2026-11-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.config import get_settings

revision: str = "0003_auth_tokens"
down_revision: str | None = "0002_platform_refresh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _grant_app_role() -> None:
    role = get_settings().app_db_role
    exists = (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role})
        .scalar()
    )
    if exists:
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON auth_tokens TO "{role}"')


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            purpose    text NOT NULL CHECK (purpose IN ('verify_email', 'reset_password')),
            token_hash bytea NOT NULL UNIQUE,
            expires_at timestamptz NOT NULL,
            used_at    timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS auth_tokens_user_purpose_idx "
        "ON auth_tokens (user_id, purpose, created_at DESC)"
    )
    _grant_app_role()


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_tokens")
