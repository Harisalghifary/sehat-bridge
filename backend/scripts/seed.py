"""Dev seed: two tenants, roles, and one identity shared across both.

Run with ``make seed``. Idempotent. Sample file rows arrive with M4, because
writing metadata for objects that do not exist would make downloads lie.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import asyncpg
from app.auth.security import hash_password
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import schema_name
from app.tenancy import service

TENANTS = [
    ("acme", "Klinik Acme", "owner-acme@example.com"),
    ("globex", "Lab Globex", "owner-globex@example.com"),
]


async def _add_member(
    email: str, slug: str, role: str, display_name: str, password_hash: str
) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    try:
        async with conn.transaction():
            user_id: UUID = await service.ensure_user(conn, email, password_hash)
            tenant_id = await conn.fetchval("SELECT id FROM public.tenants WHERE slug = $1", slug)
            await service.ensure_membership(conn, user_id, tenant_id, role)
            schema = schema_name(slug)
            await conn.execute("SELECT set_config('search_path', $1, true)", f"{schema}, public")
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant_id))
            await service.upsert_profile(conn, user_id=user_id, display_name=display_name)
    finally:
        await conn.close()


async def _ensure_password(email: str, password_hash: str) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    try:
        await service.ensure_password(conn, email, password_hash)
    finally:
        await conn.close()


async def _ensure_platform_admin(email: str, password_hash: str) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    try:
        await conn.execute(
            """
            INSERT INTO public.users (email, hashed_password, is_platform_admin)
            VALUES ($1, $2, true)
            ON CONFLICT (email) DO UPDATE
                SET is_platform_admin = true, updated_at = now()
            """,
            email,
            password_hash,
        )
    finally:
        await conn.close()


async def main() -> None:
    settings = get_settings()
    password_hash = hash_password(settings.demo_password)

    for slug, name, owner in TENANTS:
        tenant = await service.provision_tenant(
            slug=slug,
            name=name,
            owner_email=owner,
            password_hash=password_hash,
        )
        await _ensure_password(owner, password_hash)
        print(f"tenant {tenant.slug:<10} schema={tenant.schema} owner={owner}")

    # Same email, two tenants, two roles, two profiles — the membership model.
    await _add_member("same@person.dev", "acme", "admin", "Sama Person", password_hash)
    await _add_member("same@person.dev", "globex", "member", "Sama Person", password_hash)

    print("\nseed complete")
    print("  same@person.dev -> acme:admin, globex:member")
    print("  ops@sehatbridge.dev -> platform admin (no tenant)")
    await _ensure_platform_admin("ops@sehatbridge.dev", password_hash)
    print(f"  demo password for all seeded users: {settings.demo_password}")


if __name__ == "__main__":
    asyncio.run(main())
