"""Tenant provisioning, migrations, and cache resolution."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import TenantContext, schema_name

logger = logging.getLogger(__name__)

TENANT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "tenant_migrations"
CACHE_PREFIX = "sb:tenant:"
CACHE_TTL_SECONDS = 60


class ProvisioningError(RuntimeError):
    pass


def _tenant_from_row(row: Any) -> TenantContext:
    return TenantContext(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        status=row["status"],
        schema=schema_name(row["slug"]),
    )


async def provision_tenant(
    *,
    slug: str,
    name: str,
    owner_email: str,
    owner_display_name: str | None = None,
    password_hash: str | None = None,
) -> TenantContext:
    """Create a tenant schema and its owner. Idempotent for active tenants.

    The tenant row is committed *before* the schema exists, so a failure can be
    recorded as ``failed`` instead of vanishing with the transaction.
    """
    settings = get_settings()
    schema = schema_name(slug)
    role = settings.app_db_role
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    lock_key = f"tenant:{slug}"
    created = False

    try:
        await conn.execute("SELECT pg_advisory_lock(hashtext($1))", lock_key)
        existing = await conn.fetchrow(
            "SELECT id, slug, name, status FROM public.tenants WHERE slug = $1", slug
        )

        if existing and existing["status"] == "active":
            return TenantContext(
                id=existing["id"],
                slug=existing["slug"],
                name=existing["name"],
                status="active",
                schema=schema,
            )

        if existing:
            tenant_id = existing["id"]
            await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            await conn.execute(
                """
                UPDATE public.tenants
                   SET status = 'provisioning', failure_note = NULL,
                       updated_at = now()
                 WHERE id = $1
                """,
                tenant_id,
            )
        else:
            created = True
            tenant_id = await conn.fetchval(
                """
                INSERT INTO public.tenants (slug, name, status)
                VALUES ($1, $2, 'provisioning')
                RETURNING id
                """,
                slug,
                name,
            )

        try:
            async with conn.transaction():
                await conn.execute(f'CREATE SCHEMA "{schema}"')
                await conn.execute(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"')
                await conn.execute(
                    "SELECT set_config('search_path', $1, true)",
                    f"{schema}, public",
                )
                await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant_id))

                await apply_tenant_migrations(conn, schema)
                await grant_tenant_privileges(conn, schema, role)

                user_id = await ensure_user(conn, owner_email, password_hash or "!unset")
                await ensure_membership(conn, user_id, tenant_id, "owner")
                await upsert_profile(
                    conn,
                    user_id=user_id,
                    display_name=owner_display_name or owner_email.split("@", 1)[0],
                )

                await conn.execute(
                    """
                    UPDATE public.tenants
                       SET status = 'active', name = $2, updated_at = now()
                     WHERE id = $1
                    """,
                    tenant_id,
                    name,
                )
                await conn.execute(
                    """
                    INSERT INTO public.audit_log
                        (tenant_id, action, resource_type, resource_id)
                    VALUES ($1, 'tenant.provisioned', 'tenant', $2)
                    """,
                    tenant_id,
                    str(tenant_id),
                )
        except Exception as exc:
            await conn.execute(
                """
                UPDATE public.tenants
                   SET status = 'failed', failure_note = $2, updated_at = now()
                 WHERE id = $1
                """,
                tenant_id,
                str(exc)[:500],
            )
            raise ProvisioningError(f"provisioning {slug} failed: {exc}") from exc
    finally:
        try:
            await conn.execute("SELECT pg_advisory_unlock(hashtext($1))", lock_key)
        finally:
            await conn.close()

    if created:
        await invalidate_tenant_cache(slug)

    return TenantContext(
        id=tenant_id,
        slug=slug,
        name=name,
        status="active",
        schema=schema,
    )


async def apply_tenant_migrations(conn: asyncpg.Connection, schema: str) -> list[str]:
    """Apply pending SQL files in order. Caller owns the transaction."""
    applied_now: list[str] = []
    for path in sorted(TENANT_MIGRATIONS_DIR.glob("*.sql")):
        version = path.stem
        has_table = await conn.fetchval(
            "SELECT to_regclass($1) IS NOT NULL", f"{schema}.schema_migrations"
        )
        if has_table:
            done = await conn.fetchval(
                f'SELECT 1 FROM "{schema}".schema_migrations WHERE version = $1',  # noqa: S608
                version,
            )
            if done:
                continue

        await conn.execute(path.read_text(encoding="utf-8"))
        await conn.execute(
            f'INSERT INTO "{schema}".schema_migrations (version) VALUES ($1) '  # noqa: S608
            "ON CONFLICT DO NOTHING",
            version,
        )
        applied_now.append(version)
    return applied_now


async def grant_tenant_privileges(conn: asyncpg.Connection, schema: str, role: str) -> None:
    """Give the non-owner app role DML rights so RLS policies actually apply."""
    await conn.execute(
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO "{role}"'
    )
    await conn.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "{schema}" TO "{role}"')
    await conn.execute(
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{role}"'
    )
    await conn.execute(
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
        f'GRANT USAGE, SELECT ON SEQUENCES TO "{role}"'
    )


async def ensure_user(conn: asyncpg.Connection, email: str, password_hash: str) -> UUID:
    user_id: UUID = await conn.fetchval(
        """
        INSERT INTO public.users (email, hashed_password)
        VALUES ($1, $2)
        ON CONFLICT (email) DO UPDATE SET updated_at = now()
        RETURNING id
        """,
        email,
        password_hash,
    )
    return user_id


async def ensure_membership(
    conn: asyncpg.Connection, user_id: UUID, tenant_id: UUID, role: str
) -> None:
    await conn.execute(
        """
        INSERT INTO public.memberships (user_id, tenant_id, role)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, tenant_id) DO NOTHING
        """,
        user_id,
        tenant_id,
        role,
    )


async def upsert_profile(conn: asyncpg.Connection, *, user_id: UUID, display_name: str) -> None:
    await conn.execute(
        """
        INSERT INTO profiles (user_id, display_name)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE
            SET display_name = EXCLUDED.display_name, updated_at = now()
        """,
        user_id,
        display_name,
    )


async def migrate_all_tenants() -> list[tuple[str, list[str]]]:
    """Fan out pending tenant migrations. One transaction per tenant."""
    settings = get_settings()
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    results: list[tuple[str, list[str]]] = []
    try:
        rows = await conn.fetch(
            "SELECT slug FROM public.tenants WHERE status = 'active' ORDER BY slug"
        )
        for row in rows:
            slug = row["slug"]
            schema = schema_name(slug)
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", f"migrate:{slug}")
                await conn.execute(
                    "SELECT set_config('search_path', $1, true)",
                    f"{schema}, public",
                )
                applied = await apply_tenant_migrations(conn, schema)
                await grant_tenant_privileges(conn, schema, settings.app_db_role)
            results.append((slug, applied))
    finally:
        await conn.close()
    return results


async def list_tenants() -> list[tuple[str, str, str]]:
    settings = get_settings()
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    try:
        rows = await conn.fetch("SELECT slug, name, status FROM public.tenants ORDER BY slug")
        return [(row["slug"], row["name"], row["status"]) for row in rows]
    finally:
        await conn.close()


async def get_tenant_by_slug(engine: AsyncEngine, slug: str) -> TenantContext | None:
    async with engine.connect() as conn:
        row = (
            (
                await conn.execute(
                    text("SELECT id, slug, name, status FROM public.tenants WHERE slug = :slug"),
                    {"slug": slug},
                )
            )
            .mappings()
            .first()
        )
    return TenantContext(**dict(row), schema=schema_name(row["slug"])) if row else None


def _cache_key(slug: str) -> str:
    return f"{CACHE_PREFIX}{slug}"


async def cache_tenant(redis: Redis, tenant: TenantContext) -> None:
    await redis.set(
        _cache_key(tenant.slug),
        json.dumps(
            {
                "id": str(tenant.id),
                "slug": tenant.slug,
                "name": tenant.name,
                "status": tenant.status,
                "schema": tenant.schema,
            }
        ),
        ex=CACHE_TTL_SECONDS,
    )


async def resolve_tenant(
    redis: Redis | None, engine: AsyncEngine, slug: str
) -> TenantContext | None:
    if redis is not None:
        try:
            cached = await redis.get(_cache_key(slug))
        except Exception:
            logger.warning("tenant cache read failed", exc_info=True)
        else:
            if cached:
                data = json.loads(cached)
                return TenantContext(
                    id=UUID(data["id"]),
                    **{key: data[key] for key in ("slug", "name", "status", "schema")},
                )

    tenant = await get_tenant_by_slug(engine, slug)
    if tenant is not None and redis is not None and tenant.status == "active":
        try:
            await cache_tenant(redis, tenant)
        except Exception:
            logger.warning("tenant cache write failed", exc_info=True)
    return tenant


async def invalidate_tenant_cache(slug: str) -> None:
    """Best-effort cache invalidation; provisioning must not fail on Redis."""
    settings = get_settings()
    try:
        redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
        try:
            await redis.delete(_cache_key(slug))
        finally:
            await redis.aclose()
    except Exception:
        logger.warning("tenant cache invalidation failed for %s", slug, exc_info=True)


def describe(tenants: Sequence[tuple[str, str, str]]) -> str:
    return "\n".join(f"{slug:<24} {status:<12} {name}" for slug, name, status in tenants)
