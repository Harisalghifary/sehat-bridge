"""User list, role rules, and profile update integration tests."""

from __future__ import annotations

import uuid
from uuid import UUID

import asyncpg
import pytest
from app.auth.security import hash_password
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import TenantContext, schema_name
from app.tenancy import service
from httpx import AsyncClient

from tests.conftest import PASSWORD, drop_tenant

pytestmark = pytest.mark.integration


def _suffix(tenant: TenantContext) -> str:
    return tenant.slug.split("-", 1)[1]


async def _add_member(
    tenant: TenantContext,
    email: str,
    role: str,
    display_name: str = "Member",
) -> UUID:
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        async with conn.transaction():
            user_id: UUID = await conn.fetchval(
                """
                INSERT INTO public.users (email, hashed_password)
                VALUES ($1, $2)
                ON CONFLICT (email) DO UPDATE SET updated_at = now()
                RETURNING id
                """,
                email,
                hash_password(PASSWORD),
            )
            await conn.execute(
                """
                INSERT INTO public.memberships (user_id, tenant_id, role)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, tenant_id) DO UPDATE SET role = EXCLUDED.role
                """,
                user_id,
                tenant.id,
                role,
            )
            await conn.execute(
                "SELECT set_config('search_path', $1, true)",
                f"{schema_name(tenant.slug)}, public",
            )
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant.id))
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
        return user_id
    finally:
        await conn.close()


async def _login(api: AsyncClient, tenant: TenantContext, email: str) -> dict[str, object]:
    response = await api.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": tenant.slug,
            "email": email,
            "password": PASSWORD,
        },
        headers={"X-Forwarded-For": f"10.{uuid.uuid4().int % 250}.1.1"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token: str, slug: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": slug}


async def test_member_cannot_list_users(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, _ = tenant
    suffix = _suffix(current)
    email = f"member-{suffix}@sehatbridge.dev"
    await _add_member(current, email, "member")

    tokens = await _login(api, current, email)
    response = await api.get(
        "/api/v1/users",
        headers=_auth(str(tokens["access_token"]), current.slug),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "insufficient_role"


async def test_admin_lists_users_with_cursor_pagination(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    suffix = _suffix(current)
    await _add_member(current, f"a-{suffix}@sehatbridge.dev", "admin", "Admin A")
    await _add_member(current, f"b-{suffix}@sehatbridge.dev", "member", "Member B")
    await _add_member(current, f"c-{suffix}@sehatbridge.dev", "member", "Member C")

    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)

    first = await api.get("/api/v1/users?limit=2", headers=headers)
    assert first.status_code == 200, first.text
    page1 = first.json()
    assert len(page1["items"]) == 2
    assert page1["has_more"] is True
    assert page1["next_cursor"]

    second = await api.get(f"/api/v1/users?limit=2&cursor={page1['next_cursor']}", headers=headers)
    page2 = second.json()
    ids = {item["id"] for item in page1["items"]} | {item["id"] for item in page2["items"]}
    assert len(ids) == 4
    assert page2["has_more"] is False


async def test_admin_cannot_grant_or_change_owner(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, _ = tenant
    suffix = _suffix(current)
    admin_email = f"admin-{suffix}@sehatbridge.dev"
    member_email = f"member-{suffix}@sehatbridge.dev"
    admin_id = await _add_member(current, admin_email, "admin", "Admin")
    member_id = await _add_member(current, member_email, "member", "Member")

    admin_tokens = await _login(api, current, admin_email)
    headers = _auth(str(admin_tokens["access_token"]), current.slug)

    listed = await api.get("/api/v1/users", headers=headers)
    owner = next(item for item in listed.json()["items"] if item["role"] == "owner")

    demote_owner = await api.patch(
        f"/api/v1/users/{owner['id']}/role",
        json={"role": "member"},
        headers=headers,
    )
    assert demote_owner.status_code == 403

    promote_member = await api.patch(
        f"/api/v1/users/{member_id}/role",
        json={"role": "owner"},
        headers=headers,
    )
    assert promote_member.status_code == 403

    promote_self = await api.patch(
        f"/api/v1/users/{admin_id}/role",
        json={"role": "owner"},
        headers=headers,
    )
    assert promote_self.status_code == 403


async def test_owner_changes_role_and_last_owner_is_protected(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    suffix = _suffix(current)
    member_email = f"member-{suffix}@sehatbridge.dev"
    member_id = await _add_member(current, member_email, "member", "Member")

    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)

    promote = await api.patch(
        f"/api/v1/users/{member_id}/role",
        json={"role": "admin"},
        headers=headers,
    )
    assert promote.status_code == 200, promote.text
    assert promote.json()["role"] == "admin"

    me = await api.get("/api/v1/users/me", headers=headers)
    owner_id = me.json()["id"]

    demote_last_owner = await api.patch(
        f"/api/v1/users/{owner_id}/role",
        json={"role": "member"},
        headers=headers,
    )
    assert demote_last_owner.status_code == 409
    assert demote_last_owner.json()["code"] == "last_owner"


async def test_cross_tenant_user_returns_404(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    suffix = uuid.uuid4().hex[:8]
    other_slug = f"other-{suffix}"
    other_email = f"owner-{suffix}@sehatbridge.dev"
    other = await service.provision_tenant(
        slug=other_slug,
        name="Other Tenant",
        owner_email=other_email,
        password_hash=hash_password(PASSWORD),
    )
    try:
        conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
        try:
            other_user_id = await conn.fetchval(
                """
                SELECT user_id FROM public.memberships
                 WHERE tenant_id = $1 ORDER BY created_at LIMIT 1
                """,
                other.id,
            )
        finally:
            await conn.close()

        tokens = await _login(api, current, owner_email)
        response = await api.patch(
            f"/api/v1/users/{other_user_id}/role",
            json={"role": "member"},
            headers=_auth(str(tokens["access_token"]), current.slug),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "user_not_found"
    finally:
        await drop_tenant(other_slug, other_email)


async def test_patch_me_updates_profile(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)

    updated = await api.patch(
        "/api/v1/users/me",
        json={"display_name": "Dr. Acme", "timezone": "Asia/Jakarta"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_name"] == "Dr. Acme"

    me = await api.get("/api/v1/users/me", headers=headers)
    assert me.json()["profile"]["timezone"] == "Asia/Jakarta"


async def test_invalid_timezone_is_rejected(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    response = await api.patch(
        "/api/v1/users/me",
        json={"timezone": "Mars/Olympus"},
        headers=_auth(str(tokens["access_token"]), current.slug),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_timezone"


async def test_shared_identity_has_per_tenant_role_and_profile(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    first, _ = tenant
    suffix = _suffix(first)
    shared_email = f"shared-{suffix}@sehatbridge.dev"
    await _add_member(first, shared_email, "admin", "Satu")

    other_suffix = uuid.uuid4().hex[:8]
    other_slug = f"other-{other_suffix}"
    other_owner = f"owner-{other_suffix}@sehatbridge.dev"
    second = await service.provision_tenant(
        slug=other_slug,
        name="Second Tenant",
        owner_email=other_owner,
        password_hash=hash_password(PASSWORD),
    )
    try:
        await _add_member(second, shared_email, "member", "Dua")

        first_tokens = await _login(api, first, shared_email)
        first_me = await api.get(
            "/api/v1/users/me",
            headers=_auth(str(first_tokens["access_token"]), first.slug),
        )
        assert first_me.json()["membership"]["role"] == "admin"
        assert first_me.json()["profile"]["display_name"] == "Satu"
        assert first_me.json()["membership"]["tenant"]["slug"] == first.slug

        second_tokens = await _login(api, second, shared_email)
        second_me = await api.get(
            "/api/v1/users/me",
            headers=_auth(str(second_tokens["access_token"]), second.slug),
        )
        assert second_me.json()["membership"]["role"] == "member"
        assert second_me.json()["profile"]["display_name"] == "Dua"
    finally:
        await drop_tenant(other_slug, other_owner)
