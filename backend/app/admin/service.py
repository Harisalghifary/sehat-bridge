"""Cross-tenant queries used only by platform operators.

The API process still connects as the non-owner runtime role. Admin reads use
the migration DSN because they intentionally span every tenant schema; callers
must go through ``require_platform_admin``.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg

from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import schema_name

TENANT_SELECT = """
    SELECT t.slug, t.name, t.status, t.plan, t.failure_note,
           t.created_at, t.updated_at,
           count(m.user_id)::int AS members,
           (array_agg(u.email ORDER BY m.created_at ASC)
              FILTER (WHERE m.role = 'owner'))[1] AS owner_email
      FROM public.tenants t
      LEFT JOIN public.memberships m ON m.tenant_id = t.id
      LEFT JOIN public.users u ON u.id = m.user_id
     GROUP BY t.id
"""


async def _connect() -> asyncpg.Connection:
    settings = get_settings()
    return await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))


async def list_tenants_admin() -> list[dict[str, Any]]:
    conn = await _connect()
    try:
        rows = await conn.fetch(f"{TENANT_SELECT} ORDER BY t.created_at DESC")
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_tenant_admin(slug: str) -> dict[str, Any] | None:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            f"SELECT * FROM ({TENANT_SELECT}) q WHERE q.slug = $1",  # noqa: S608
            slug,
        )
        if row is None:
            return None

        schema = schema_name(row["slug"])
        table = await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"{schema}.sync_jobs")
        queued = failed = 0
        if table:
            counts = await conn.fetchrow(
                f"""
                SELECT count(*) FILTER (WHERE status IN ('queued', 'running'))::int AS queued,
                       count(*) FILTER (WHERE status IN ('failed', 'dead'))::int AS failed
                  FROM "{schema}".sync_jobs
                """  # noqa: S608
            )
            queued = counts["queued"] if counts else 0
            failed = counts["failed"] if counts else 0

        data = dict(row)
        data["queued_jobs"] = queued
        data["failed_jobs"] = failed
        return data
    finally:
        await conn.close()


async def record_audit(
    *,
    tenant_id: UUID | None,
    actor_user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    conn = await _connect()
    try:
        await conn.execute(
            """
            INSERT INTO public.audit_log
                (tenant_id, actor_user_id, action, resource_type, resource_id, metadata)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            tenant_id,
            actor_user_id,
            action,
            resource_type,
            resource_id,
            None if metadata is None else json.dumps(metadata),
        )
    finally:
        await conn.close()


async def set_tenant_status(
    *, slug: str, target: str, action: str, actor_user_id: UUID
) -> dict[str, Any] | None:
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            """
            UPDATE public.tenants
               SET status = $2::tenant_status, updated_at = now()
             WHERE slug = $1
               AND status = $3::tenant_status
            RETURNING id, slug
            """,
            slug,
            target,
            "active" if target == "suspended" else "suspended",
        )
        if row is None:
            return None

        await conn.execute(
            """
            INSERT INTO public.audit_log
                (tenant_id, actor_user_id, action, resource_type, resource_id)
            VALUES ($1, $2, $3, 'tenant', $4)
            """,
            row["id"],
            actor_user_id,
            action,
            slug,
        )
        return await get_tenant_admin(slug)
    finally:
        await conn.close()


async def tenant_status_counts() -> dict[str, int]:
    conn = await _connect()
    try:
        rows = await conn.fetch(
            "SELECT status::text AS status, count(*)::int AS count "
            "FROM public.tenants GROUP BY status"
        )
        counts = {"active": 0, "suspended": 0, "provisioning": 0, "failed": 0}
        for row in rows:
            counts[row["status"]] = row["count"]
        return counts
    finally:
        await conn.close()


async def queue_depth() -> dict[str, int]:
    conn = await _connect()
    try:
        rows = await conn.fetch("SELECT slug FROM public.tenants WHERE status = 'active'")
        totals = {"queued": 0, "running": 0, "failed": 0, "dead": 0}
        for row in rows:
            schema = schema_name(row["slug"])
            exists = await conn.fetchval(
                "SELECT to_regclass($1) IS NOT NULL", f"{schema}.sync_jobs"
            )
            if not exists:
                continue
            counts = await conn.fetchrow(
                f"""
                SELECT count(*) FILTER (WHERE status = 'queued')::int AS queued,
                       count(*) FILTER (WHERE status = 'running')::int AS running,
                       count(*) FILTER (WHERE status = 'failed')::int AS failed,
                       count(*) FILTER (WHERE status = 'dead')::int AS dead
                  FROM "{schema}".sync_jobs
                """  # noqa: S608
            )
            if counts:
                for key in totals:
                    totals[key] += counts[key]
        return totals
    finally:
        await conn.close()


async def audit_actions() -> list[str]:
    conn = await _connect()
    try:
        rows = await conn.fetch("SELECT DISTINCT action FROM public.audit_log ORDER BY action ASC")
        return [row["action"] for row in rows]
    finally:
        await conn.close()


async def query_audit(
    *,
    tenant_slug: str | None,
    action: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    clauses: list[str] = []
    args: list[Any] = []

    def add(clause: str, value: Any) -> None:
        args.append(value)
        clauses.append(clause.format(n=len(args)))

    if tenant_slug:
        add("t.slug = ${n}", tenant_slug)
    if action:
        add("a.action = ${n}", action)
    if created_from:
        add("a.created_at >= ${n}", created_from)
    if created_to:
        add("a.created_at < ${n}", created_to)

    where = " AND ".join(clauses) if clauses else "TRUE"
    conn = await _connect()
    try:
        total = await conn.fetchval(
            f"""
            SELECT count(*)
              FROM public.audit_log a
              LEFT JOIN public.tenants t ON t.id = a.tenant_id
             WHERE {where}
            """,  # noqa: S608
            *args,
        )
        rows = await conn.fetch(
            f"""
            SELECT a.id, a.action, a.resource_type, a.resource_id,
                   a.metadata, a.created_at,
                   t.slug AS tenant_slug, t.name AS tenant_name,
                   u.email AS actor_email
              FROM public.audit_log a
              LEFT JOIN public.tenants t ON t.id = a.tenant_id
              LEFT JOIN public.users u ON u.id = a.actor_user_id
             WHERE {where}
             ORDER BY a.created_at DESC, a.id DESC
             LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
            """,  # noqa: S608
            *args,
            limit,
            offset,
        )
        items = []
        for row in rows:
            data = dict(row)
            metadata = data.get("metadata")
            if isinstance(metadata, str):
                data["metadata"] = json.loads(metadata)
            elif metadata is None:
                data["metadata"] = {}
            items.append(data)
        return items, int(total or 0)
    finally:
        await conn.close()
