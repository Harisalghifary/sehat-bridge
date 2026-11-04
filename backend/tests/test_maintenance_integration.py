"""Retention deletes only rows older than the configured windows."""

from __future__ import annotations

import uuid

import asyncpg
import pytest
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.maintenance import run_retention

pytestmark = pytest.mark.integration


async def test_retention_removes_old_rows_only() -> None:
    suffix = uuid.uuid4().hex[:8]
    old_lead = f"old-{suffix}@example.com"
    new_lead = f"new-{suffix}@example.com"
    old_action = f"test.old.{suffix}"
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        await conn.execute(
            """
            INSERT INTO public.leads (name, email, facility_name, created_at)
            VALUES ('Old', $1, 'Old Klinik', now() - interval '400 days'),
                   ('New', $2, 'New Klinik', now())
            """,
            old_lead,
            new_lead,
        )
        await conn.execute(
            """
            INSERT INTO public.audit_log (action, created_at)
            VALUES ($1, now() - interval '400 days'),
                   ($2, now())
            """,
            old_action,
            f"{old_action}.recent",
        )
    finally:
        await conn.close()

    try:
        counts = await run_retention()
        assert counts["leads"] >= 1
        assert counts["audit_rows"] >= 1

        conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
        try:
            leads = {
                row["email"]
                for row in await conn.fetch(
                    "SELECT email FROM public.leads WHERE email = ANY($1::text[])",
                    [old_lead, new_lead],
                )
            }
            actions = {
                row["action"]
                for row in await conn.fetch(
                    "SELECT action FROM public.audit_log WHERE action LIKE $1",
                    f"{old_action}%",
                )
            }
        finally:
            await conn.close()
        assert leads == {new_lead}
        assert actions == {f"{old_action}.recent"}
    finally:
        conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
        try:
            await conn.execute(
                "DELETE FROM public.leads WHERE email = ANY($1::text[])",
                [old_lead, new_lead],
            )
            await conn.execute(
                "DELETE FROM public.audit_log WHERE action LIKE $1", f"{old_action}%"
            )
        finally:
            await conn.close()
