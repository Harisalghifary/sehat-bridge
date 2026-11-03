"""Authentication integration tests (Postgres + Redis)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest
from app.auth.security import hash_password
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import TenantContext
from app.tenancy import service
from httpx import AsyncClient

from tests.conftest import drop_tenant

pytestmark = pytest.mark.integration

PASSWORD = "demo-password-123"


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    # Unique source IP per call keeps the per-IP register limiter out of the way.
    headers = {"X-Forwarded-For": f"10.{uuid.uuid4().int % 250}.0.1"}
    if extra:
        headers.update(extra)
    return headers


async def _purge_users(pattern: str) -> None:
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        await conn.execute("DELETE FROM public.users WHERE email LIKE $1", pattern)
    finally:
        await conn.close()


@pytest.fixture
async def tenant(
    migrated_database: None,
) -> AsyncIterator[tuple[TenantContext, str]]:
    suffix = uuid.uuid4().hex[:8]
    slug = f"auth-{suffix}"
    email = f"owner-{suffix}@sehatbridge.dev"
    created = await service.provision_tenant(
        slug=slug,
        name="Auth Test",
        owner_email=email,
        password_hash=hash_password(PASSWORD),
    )
    try:
        yield created, email
    finally:
        await drop_tenant(slug, email)
        await _purge_users(f"%-{suffix}@sehatbridge.dev")


async def _login(
    api: AsyncClient,
    tenant: TenantContext,
    *,
    email: str,
    password: str = PASSWORD,
):
    return await api.post(
        "/api/v1/auth/login",
        json={"tenant_slug": tenant.slug, "email": email, "password": password},
        headers=_headers(),
    )


async def test_register_returns_tokens_and_profile(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, _ = tenant
    suffix = current.slug.split("-", 1)[1]
    email = f"new-{suffix}@sehatbridge.dev"

    response = await api.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": current.slug,
            "email": email,
            "password": PASSWORD,
            "display_name": "New User",
        },
        headers=_headers(),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "member"
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900

    me = await api.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {body['access_token']}",
            "X-Tenant-ID": current.slug,
        },
    )
    assert me.status_code == 200, me.text
    assert me.json()["profile"]["display_name"] == "New User"
    assert me.json()["membership"]["tenant"]["slug"] == current.slug


async def test_wrong_password_and_unknown_tenant_are_uniform(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, email = tenant

    wrong = await _login(api, current, email=email, password="wrong-password")
    unknown = await api.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "does-not-exist", "email": email, "password": PASSWORD},
        headers=_headers(),
    )

    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json()["code"] == "invalid_credentials"
    assert unknown.json()["code"] == "invalid_credentials"
    assert wrong.json().get("detail") == unknown.json().get("detail")


async def test_refresh_rotation_and_reuse_revokes_the_family(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, email = tenant
    login = await _login(api, current, email=email)
    first_refresh = login.json()["refresh_token"]

    rotated = await api.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert rotated.status_code == 200, rotated.text
    second_refresh = rotated.json()["refresh_token"]
    assert second_refresh != first_refresh

    reused = await api.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert reused.status_code == 401
    assert reused.json()["code"] == "invalid_refresh"

    revoked = await api.post("/api/v1/auth/refresh", json={"refresh_token": second_refresh})
    assert revoked.status_code == 401


async def test_logout_blacklists_the_access_token(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, email = tenant
    login = await _login(api, current, email=email)
    tokens = login.json()
    auth = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-Tenant-ID": current.slug,
    }

    assert (await api.get("/api/v1/users/me", headers=auth)).status_code == 200

    logout = await api.post("/api/v1/auth/logout", json={"all_sessions": True}, headers=auth)
    assert logout.status_code == 204

    after = await api.get("/api/v1/users/me", headers=auth)
    assert after.status_code == 401
    assert after.json()["code"] == "token_revoked"

    refresh = await api.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 401


async def test_tenant_header_must_match_the_token(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, email = tenant
    suffix = uuid.uuid4().hex[:8]
    other_slug = f"other-{suffix}"
    other_email = f"other-{suffix}@sehatbridge.dev"
    other = await service.provision_tenant(
        slug=other_slug,
        name="Other",
        owner_email=other_email,
        password_hash=hash_password(PASSWORD),
    )
    try:
        login = await _login(api, current, email=email)
        token = login.json()["access_token"]
        response = await api.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": other.slug,
            },
        )
        assert response.status_code == 403
        assert response.json()["code"] == "tenant_mismatch"
    finally:
        await drop_tenant(other_slug, other_email)


async def test_platform_login_has_no_tenant(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    _, _ = tenant
    suffix = uuid.uuid4().hex[:8]
    email = f"ops-{suffix}@sehatbridge.dev"
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        await conn.execute(
            """
            INSERT INTO public.users (email, hashed_password, is_platform_admin)
            VALUES ($1, $2, true)
            """,
            email,
            hash_password(PASSWORD),
        )
        response = await api.post(
            "/api/v1/auth/platform-login",
            json={"email": email, "password": PASSWORD},
            headers=_headers(),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["scope"] == "platform"
        assert body["user"]["role"] is None

        me = await api.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["membership"] is None
        assert me.json()["is_platform_admin"] is True
    finally:
        await conn.execute("DELETE FROM public.users WHERE email = $1", email)
        await conn.close()


async def test_login_is_rate_limited(api: AsyncClient, tenant: tuple[TenantContext, str]) -> None:
    current, _ = tenant
    email = f"ratelimit-{uuid.uuid4().hex[:8]}@sehatbridge.dev"

    for _ in range(5):
        attempt = await _login(api, current, email=email, password="wrong-password")
        assert attempt.status_code == 401

    blocked = await _login(api, current, email=email, password="wrong-password")
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"
    assert int(blocked.headers["Retry-After"]) > 0


async def test_weak_password_is_rejected(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, _ = tenant
    response = await api.post(
        "/api/v1/auth/register",
        json={
            "tenant_slug": current.slug,
            "email": f"weak-{uuid.uuid4().hex[:8]}@sehatbridge.dev",
            "password": "short",
        },
        headers=_headers(),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "weak_password"
