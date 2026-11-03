"""Platform refresh tokens have no tenant.

Revision ID: 0002_platform_refresh
Revises: 0001_public
Create Date: 2026-11-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_platform_refresh"
down_revision: str | None = "0001_public"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE refresh_tokens ALTER COLUMN tenant_id DROP NOT NULL")


def downgrade() -> None:
    op.execute("DELETE FROM refresh_tokens WHERE tenant_id IS NULL")
    op.execute("ALTER TABLE refresh_tokens ALTER COLUMN tenant_id SET NOT NULL")
