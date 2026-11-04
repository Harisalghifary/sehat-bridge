"""Retention jobs for audit rows, leads, and spent auth tokens."""

from __future__ import annotations

import asyncpg

from app.config import get_settings
from app.db.engine import asyncpg_dsn


async def run_retention() -> dict[str, int]:
    settings = get_settings()
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    try:
        audit = await conn.execute(
            "DELETE FROM public.audit_log "
            "WHERE created_at < now() - (CAST($1 AS integer) * interval '1 day')",
            settings.audit_retention_days,
        )
        leads = await conn.execute(
            "DELETE FROM public.leads "
            "WHERE created_at < now() - (CAST($1 AS integer) * interval '1 day')",
            settings.lead_retention_days,
        )
        tokens = await conn.execute(
            "DELETE FROM public.auth_tokens "
            "WHERE expires_at < now() - interval '1 day' OR used_at IS NOT NULL"
        )
        return {
            "audit_rows": _rowcount(audit),
            "leads": _rowcount(leads),
            "auth_tokens": _rowcount(tokens),
        }
    finally:
        await conn.close()


def _rowcount(status: str) -> int:
    try:
        return int(status.split()[-1])
    except (ValueError, IndexError):
        return 0
