"""Platform operator API tests: guards, provisioning, suspension, audit."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import asyncpg
import httpx
import pytest
from app.auth.security import hash_password
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import TenantContext
from httpx import AsyncClient

from tests.conftest import PASSWORD, drop_tenant

pytestmark = pytest.mark.integration


async def _create_platform(email: str) -> None:
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        await conn.execute(
            """
            INSERT INTO public.users (email, hashed_password, is_platform_admin)
            VALUES ($1, $2, true)
            ON CONFLICT (email) DO UPDATE
                SET is_platform_admin = true, hashed_password = EXCLUDED.hashed_password
            """,
            email,
            hash_password(PASSWORD),
        )
    finally:
        await conn.close()


@pytest.fixture
async def operator(api: AsyncClient) -> AsyncIterator[tuple[str, str]]:
    suffix = uuid.uuid4().hex[:8]
    email = f"ops-{suffix}@sehatbridge.dev"
    await _create_platform(email)
    response = await api.post(
        "/api/v1/auth/platform-login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    try:
        yield token, email
    finally:
        conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
        try:
            await conn.execute("DELETE FROM public.users WHERE email = $1", email)
        finally:
            await conn.close()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login_tenant(
    api: AsyncClient, slug: str, email: str, password: str = PASSWORD
) -> httpx.Response:
    return await api.post(
        "/api/v1/auth/login",
        json={"tenant_slug": slug, "email": email, "password": password},
    )


async def test_admin_requires_platform_scope(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    missing = await api.get("/api/v1/admin/tenants")
    assert missing.status_code == 401
    assert missing.json()["code"] == "missing_token"

    current, owner_email = tenant
    login = await _login_tenant(api, current.slug, owner_email)
    assert login.status_code == 200
    denied = await api.get("/api/v1/admin/tenants", headers=_headers(login.json()["access_token"]))
    assert denied.status_code == 403
    assert denied.json()["code"] == "platform_required"


async def test_provision_list_detail_and_audit(api: AsyncClient, operator: tuple[str, str]) -> None:
    token, _ = operator
    suffix = uuid.uuid4().hex[:8]
    slug = f"ops-{suffix}"
    owner = f"owner-{suffix}@sehatbridge.dev"
    try:
        created = await api.post(
            "/api/v1/admin/tenants",
            headers=_headers(token),
            json={
                "slug": slug,
                "name": "Klinik Operator",
                "owner_email": owner,
                "owner_display_name": "Pemilik Operator",
                "password": "temporary-pass-123",
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["tenant"]["slug"] == slug
        assert body["tenant"]["status"] == "active"
        assert [step["status"] for step in body["steps"]] == ["done", "done", "done"]

        listed = await api.get("/api/v1/admin/tenants", headers=_headers(token))
        assert listed.status_code == 200
        assert slug in {item["slug"] for item in listed.json()["items"]}

        detail = await api.get(f"/api/v1/admin/tenants/{slug}", headers=_headers(token))
        assert detail.status_code == 200
        assert detail.json()["members"] == 1
        assert detail.json()["queued_jobs"] == 0

        owner_login = await _login_tenant(api, slug, owner, "temporary-pass-123")
        assert owner_login.status_code == 200

        audit = await api.get(
            "/api/v1/admin/audit",
            headers=_headers(token),
            params={"tenant": slug, "action": "tenant.provisioned_by_platform"},
        )
        assert audit.status_code == 200
        assert audit.json()["total"] == 1
        assert audit.json()["items"][0]["tenant_slug"] == slug

        actions = await api.get("/api/v1/admin/audit/actions", headers=_headers(token))
        assert "tenant.provisioned_by_platform" in actions.json()
    finally:
        await drop_tenant(slug, owner)


async def test_suspend_blocks_login_and_resume_restores(
    api: AsyncClient, operator: tuple[str, str]
) -> None:
    token, _ = operator
    suffix = uuid.uuid4().hex[:8]
    slug = f"susp-{suffix}"
    owner = f"owner-{suffix}@sehatbridge.dev"
    try:
        created = await api.post(
            "/api/v1/admin/tenants",
            headers=_headers(token),
            json={
                "slug": slug,
                "name": "Klinik Suspend",
                "owner_email": owner,
                "password": "temporary-pass-123",
            },
        )
        assert created.status_code == 201, created.text
        owner_login = await _login_tenant(api, slug, owner, "temporary-pass-123")
        access = owner_login.json()["access_token"]

        suspended = await api.post(f"/api/v1/admin/tenants/{slug}/suspend", headers=_headers(token))
        assert suspended.status_code == 200
        assert suspended.json()["tenant"]["status"] == "suspended"

        blocked_login = await _login_tenant(api, slug, owner, "temporary-pass-123")
        assert blocked_login.status_code == 401
        assert blocked_login.json()["code"] == "invalid_credentials"

        blocked_api = await api.get("/api/v1/users/me", headers=_headers(access))
        assert blocked_api.status_code == 403
        assert blocked_api.json()["code"] == "tenant_inactive"

        resumed = await api.post(f"/api/v1/admin/tenants/{slug}/resume", headers=_headers(token))
        assert resumed.status_code == 200
        assert resumed.json()["tenant"]["status"] == "active"

        restored = await _login_tenant(api, slug, owner, "temporary-pass-123")
        assert restored.status_code == 200

        audit = await api.get(
            "/api/v1/admin/audit",
            headers=_headers(token),
            params={"tenant": slug, "action": "tenant.suspended"},
        )
        assert audit.json()["total"] == 1
    finally:
        await drop_tenant(slug, owner)


async def test_ops_health_reports_dependencies_and_queue(
    api: AsyncClient, operator: tuple[str, str]
) -> None:
    token, email = operator
    me = await api.get("/api/v1/admin/me", headers=_headers(token))
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["is_platform_admin"] is True
    assert me.json()["membership"] is None

    response = await api.get("/api/v1/admin/health", headers=_headers(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"postgres": "ok", "redis": "ok", "minio": "ok"}
    assert body["uptime_seconds"] >= 0
    assert set(body["queue"]) == {"queued", "running", "failed", "dead"}
    assert set(body["tenants"]) == {"active", "suspended", "provisioning", "failed"}
    assert all(value >= 0 for value in body["tenants"].values())


async def test_migrate_tenants_runs_fan_out(api: AsyncClient, operator: tuple[str, str]) -> None:
    token, _ = operator
    response = await api.post("/api/v1/admin/migrations/tenants", headers=_headers(token))
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert isinstance(results, list)
    assert all({"slug", "applied"} <= set(item) for item in results)
