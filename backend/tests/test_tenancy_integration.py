"""Tenant isolation integration tests.

These require a live PostgreSQL with the public schema migrated. Run with:

    make up
    cd backend && uv run pytest -m integration
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from app.config import get_settings
from app.db.engine import asyncpg_dsn, make_engine, make_sessionmaker
from app.db.session import tenant_session
from app.db.tenant_context import TenantContext, schema_name
from app.tenancy import service
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.integration

BACKEND_ROOT = Path(__file__).resolve().parents[1]


async def _ensure_app_role() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1", settings.app_db_role
        )
        if not exists:
            await conn.execute(f"CREATE ROLE \"{settings.app_db_role}\" LOGIN PASSWORD 'sehat_app'")
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def migrated_database() -> None:
    asyncio.run(_ensure_app_role())
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture
async def app_engine(migrated_database: None) -> AsyncIterator[AsyncEngine]:
    engine = make_engine(get_settings().database_url, pool_size=2)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def pair(migrated_database: None) -> AsyncIterator[tuple[TenantContext, TenantContext]]:
    suffix = uuid.uuid4().hex[:8]
    slugs = (f"t1-{suffix}", f"t2-{suffix}")
    tenants = (
        await service.provision_tenant(
            slug=slugs[0], name="Tenant One", owner_email=f"one-{suffix}@example.test"
        ),
        await service.provision_tenant(
            slug=slugs[1], name="Tenant Two", owner_email=f"two-{suffix}@example.test"
        ),
    )
    try:
        yield tenants
    finally:
        conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
        try:
            for tenant in tenants:
                await conn.execute(f'DROP SCHEMA IF EXISTS "{tenant.schema}" CASCADE')
            await conn.execute(
                "DELETE FROM public.tenants WHERE slug = ANY($1::text[])",
                list(slugs),
            )
            await conn.execute(
                "DELETE FROM public.users WHERE email LIKE $1", f"%-{suffix}@example.test"
            )
        finally:
            await conn.close()


async def _add_profile(engine: AsyncEngine, tenant: TenantContext, name: str) -> None:
    sessionmaker = make_sessionmaker(engine)
    async with tenant_session(sessionmaker, tenant) as session:
        await session.execute(
            text(
                """
                INSERT INTO profiles (user_id, display_name)
                VALUES (gen_random_uuid(), :name)
                """
            ),
            {"name": name},
        )


async def test_provisioning_is_idempotent(
    pair: tuple[TenantContext, TenantContext], app_engine: AsyncEngine
) -> None:
    first = pair[0]
    again = await service.provision_tenant(
        slug=first.slug, name=first.name, owner_email="ignored@example.test"
    )
    assert again.id == first.id
    assert again.status == "active"

    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        versions = await conn.fetchval(
            f'SELECT count(*) FROM "{first.schema}".schema_migrations'  # noqa: S608
        )
    finally:
        await conn.close()
    assert versions == len(list(service.TENANT_MIGRATIONS_DIR.glob("*.sql")))


async def test_interleaved_sessions_do_not_bleed(
    pair: tuple[TenantContext, TenantContext], app_engine: AsyncEngine
) -> None:
    one, two = pair
    await _add_profile(app_engine, one, "one-only")
    await _add_profile(app_engine, two, "two-only")

    sessionmaker = make_sessionmaker(app_engine)

    async def read(tenant: TenantContext) -> list[str]:
        async with tenant_session(sessionmaker, tenant) as session:
            await session.execute(text("SELECT pg_sleep(0.05)"))
            result = await session.execute(text("SELECT display_name FROM profiles"))
            return list(result.scalars().all())

    got_one, got_two = await asyncio.gather(read(one), read(two))
    assert "one-only" in got_one
    assert "two-only" not in got_one
    assert "two-only" in got_two
    assert "one-only" not in got_two


async def test_rls_denies_rows_without_tenant_setting(
    pair: tuple[TenantContext, TenantContext], app_engine: AsyncEngine
) -> None:
    tenant = pair[0]
    await _add_profile(app_engine, tenant, "visible-with-setting")

    async with app_engine.begin() as conn:
        await conn.execute(
            text("SELECT set_config('search_path', :path, true)"),
            {"path": f"{tenant.schema}, public"},
        )
        count = (await conn.execute(text("SELECT count(*) FROM profiles"))).scalar()

    assert count == 0


async def test_failed_provisioning_leaves_no_active_schema(
    migrated_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    suffix = uuid.uuid4().hex[:8]
    slug = f"bad-{suffix}"

    async def explode(*_args: object, **_kwargs: object) -> list[str]:
        raise RuntimeError("migration exploded")

    monkeypatch.setattr(service, "apply_tenant_migrations", explode)
    with pytest.raises(service.ProvisioningError):
        await service.provision_tenant(
            slug=slug, name="Broken", owner_email=f"broken-{suffix}@example.test"
        )

    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        status = await conn.fetchval("SELECT status FROM public.tenants WHERE slug = $1", slug)
        schema = await conn.fetchval(
            "SELECT to_regclass($1) IS NOT NULL", f"{schema_name(slug)}.profiles"
        )
        await conn.execute("DELETE FROM public.tenants WHERE slug = $1", slug)
    finally:
        await conn.close()

    assert status == "failed"
    assert schema is False


async def test_schemas_do_not_drift(
    pair: tuple[TenantContext, TenantContext],
) -> None:
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    query = """
        SELECT table_name, column_name, data_type, is_nullable, column_default
          FROM information_schema.columns
         WHERE table_schema = $1
         ORDER BY table_name, ordinal_position
    """
    try:
        one = await conn.fetch(query, pair[0].schema)
        two = await conn.fetch(query, pair[1].schema)
    finally:
        await conn.close()

    assert _normalise(one, pair[0].schema) == _normalise(two, pair[1].schema)
    assert one, "expected tenant tables to exist"


def _normalise(rows: list[asyncpg.Record], schema: str) -> list[dict[str, object]]:
    normalised = []
    for row in rows:
        item = dict(row)
        if item.get("column_default"):
            item["column_default"] = str(item["column_default"]).replace(f"{schema}.", "")
        normalised.append(item)
    return normalised


async def test_migrate_all_is_idempotent(
    pair: tuple[TenantContext, TenantContext], migrated_database: None
) -> None:
    results = dict(await service.migrate_all_tenants())
    assert results.get(pair[0].slug) == []
    assert results.get(pair[1].slug) == []
