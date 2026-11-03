from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from app.auth.security import hash_password
from app.config import get_settings
from app.db.engine import asyncpg_dsn, make_engine, make_sessionmaker
from app.db.tenant_context import TenantContext, schema_name
from app.main import create_app
from app.tenancy import service
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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


async def drop_tenant(slug: str, owner_email: str | None = None) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    try:
        await conn.execute(f'DROP SCHEMA IF EXISTS "{schema_name(slug)}" CASCADE')
        await conn.execute("DELETE FROM public.tenants WHERE slug = $1", slug)
        if owner_email:
            await conn.execute("DELETE FROM public.users WHERE email = $1", owner_email)
    finally:
        await conn.close()


@pytest.fixture
async def api(migrated_database: None) -> AsyncIterator[AsyncClient]:
    settings = get_settings()
    app = create_app()
    app.state.engine = make_engine(settings.database_url, pool_size=2)
    app.state.sessionmaker = make_sessionmaker(app.state.engine)
    app.state.redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        await app.state.redis.aclose()
        await app.state.engine.dispose()


PASSWORD = "demo-password-123"


@pytest.fixture
async def tenant(
    migrated_database: None,
) -> AsyncIterator[tuple[TenantContext, str]]:
    suffix = uuid.uuid4().hex[:8]
    slug = f"auth-{suffix}"
    email = f"owner-{suffix}@sehatbridge.dev"
    created = await service.provision_tenant(
        slug=slug,
        name="Test Tenant",
        owner_email=email,
        password_hash=hash_password(PASSWORD),
    )
    try:
        yield created, email
    finally:
        await drop_tenant(slug, email)
        conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
        try:
            await conn.execute(
                "DELETE FROM public.users WHERE email LIKE $1",
                f"%-{suffix}@sehatbridge.dev",
            )
        finally:
            await conn.close()
