"""End-to-end file flow: policy, quota, verification, download, delete."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any
from uuid import UUID

import asyncpg
import httpx
import pytest
from app.auth.security import hash_password
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import TenantContext, schema_name
from app.tenancy import service
from httpx import AsyncClient

from tests.conftest import PASSWORD, drop_tenant

pytestmark = pytest.mark.integration

PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"


def _auth(token: str, slug: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": slug}


async def _login(api: AsyncClient, tenant: TenantContext, email: str) -> dict[str, Any]:
    response = await api.post(
        "/api/v1/auth/login",
        json={"tenant_slug": tenant.slug, "email": email, "password": PASSWORD},
        headers={"X-Forwarded-For": f"10.{uuid.uuid4().int % 250}.2.1"},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


async def _presign(
    api: AsyncClient,
    headers: dict[str, str],
    *,
    filename: str = "report.pdf",
    content_type: str = "application/pdf",
    size: int = len(PDF),
) -> httpx.Response:
    return await api.post(
        "/api/v1/files/presign-upload",
        json={
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size,
        },
        headers=headers,
    )


async def _post_object(
    presigned: dict[str, Any],
    body: bytes,
    *,
    content_type: str | None = None,
) -> httpx.Response:
    upload = presigned["upload"]
    fields = dict(upload["fields"])
    if content_type is not None:
        fields["Content-Type"] = content_type
    async with httpx.AsyncClient(timeout=60) as client:
        return await client.post(
            upload["url"],
            data=fields,
            headers={"Origin": get_settings().site_url},
            files={
                "file": (
                    presigned.get("filename", "report.pdf"),
                    body,
                    content_type or fields["Content-Type"],
                )
            },
        )


async def _upload_pdf(api: AsyncClient, headers: dict[str, str]) -> tuple[UUID, dict[str, Any]]:
    presigned = await _presign(api, headers)
    assert presigned.status_code == 200, presigned.text
    payload = presigned.json()
    posted = await _post_object(payload, PDF)
    assert posted.status_code in {200, 204}, posted.text
    assert posted.headers.get("access-control-allow-origin") == get_settings().site_url
    return UUID(payload["file_id"]), payload


async def _insert_file(
    tenant: TenantContext,
    owner_id: UUID,
    *,
    status: str = "ready",
    size: int = 10,
) -> UUID:
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('search_path', $1, true)",
                f"{schema_name(tenant.slug)}, public",
            )
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant.id))
            file_id: UUID = await conn.fetchval(
                """
                INSERT INTO files
                    (tenant_id, owner_user_id, object_key, filename,
                     content_type, size_bytes, status, completed_at)
                VALUES ($1, $2, $3, $4, 'text/plain', $5, $6::file_status,
                        CASE WHEN $6 = 'ready' THEN now() END)
                RETURNING id
                """,
                tenant.id,
                owner_id,
                f"tenants/{tenant.id}/{uuid.uuid4()}/note.txt",
                "note.txt",
                size,
                status,
            )
        return file_id
    finally:
        await conn.close()


async def _add_member(tenant: TenantContext, email: str, role: str) -> UUID:
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
                INSERT INTO profiles (user_id, display_name) VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id,
                "Member",
            )
        return user_id
    finally:
        await conn.close()


async def test_upload_complete_download_delete(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)

    file_id, payload = await _upload_pdf(api, headers)
    assert payload["upload"]["method"] == "POST"
    assert payload["upload"]["expires_in"] == 600

    completed = await api.post(f"/api/v1/files/{file_id}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    body = completed.json()
    assert body["status"] == "ready"
    assert body["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert body["size_bytes"] == len(PDF)

    double = await api.post(f"/api/v1/files/{file_id}/complete", headers=headers)
    assert double.status_code == 409
    assert double.json()["code"] == "already_completed"

    link = await api.get(f"/api/v1/files/{file_id}/download", headers=headers)
    assert link.status_code == 200, link.text
    assert link.json()["expires_in"] == 300
    async with httpx.AsyncClient() as client:
        downloaded = await client.get(link.json()["url"])
    assert downloaded.status_code == 200
    assert downloaded.content == PDF

    listing = await api.get("/api/v1/files", headers=headers)
    assert listing.status_code == 200
    assert any(item["id"] == str(file_id) for item in listing.json()["items"])

    deleted = await api.delete(f"/api/v1/files/{file_id}", headers=headers)
    assert deleted.status_code == 204
    again = await api.delete(f"/api/v1/files/{file_id}", headers=headers)
    assert again.status_code == 204

    gone = await api.get(f"/api/v1/files/{file_id}/download", headers=headers)
    assert gone.status_code == 404

    hidden = await api.get("/api/v1/files", headers=headers)
    assert all(item["id"] != str(file_id) for item in hidden.json()["items"])
    with_deleted = await api.get("/api/v1/files?status=deleted", headers=headers)
    assert any(item["id"] == str(file_id) for item in with_deleted.json()["items"])


async def test_policy_rejects_oversize_body(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)
    settings = get_settings()

    app_level = await _presign(api, headers, size=settings.max_file_bytes + 1)
    assert app_level.status_code == 413
    assert app_level.json()["code"] == "file_too_large"

    presigned = await _presign(api, headers, size=settings.max_file_bytes)
    assert presigned.status_code == 200, presigned.text
    oversized = b"x" * (settings.max_file_bytes + 1024)
    posted = await _post_object(presigned.json(), oversized)
    assert posted.status_code == 400
    assert "EntityTooLarge" in posted.text or "too large" in posted.text.lower()


async def test_policy_rejects_wrong_content_type(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)

    presigned = await _presign(api, headers)
    assert presigned.status_code == 200
    posted = await _post_object(presigned.json(), PDF, content_type="text/plain")
    assert posted.status_code in {400, 403}


async def test_complete_before_upload_returns_404(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)

    presigned = await _presign(api, headers)
    file_id = presigned.json()["file_id"]
    completed = await api.post(f"/api/v1/files/{file_id}/complete", headers=headers)
    assert completed.status_code == 404
    assert completed.json()["code"] == "object_not_found"


async def test_expired_upload_is_rejected(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)

    presigned = await _presign(api, headers)
    file_id = presigned.json()["file_id"]

    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('search_path', $1, true)",
                f"{schema_name(current.slug)}, public",
            )
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(current.id))
            await conn.execute(
                "UPDATE files SET created_at = now() - interval '20 minutes' WHERE id = $1",
                UUID(file_id),
            )
    finally:
        await conn.close()

    completed = await api.post(f"/api/v1/files/{file_id}/complete", headers=headers)
    assert completed.status_code == 410
    assert completed.json()["code"] == "upload_expired"


async def test_cross_tenant_file_is_invisible(
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
            other_owner_id = await conn.fetchval(
                "SELECT user_id FROM public.memberships WHERE tenant_id = $1 LIMIT 1",
                other.id,
            )
        finally:
            await conn.close()
        foreign_file = await _insert_file(other, other_owner_id)

        tokens = await _login(api, current, owner_email)
        headers = _auth(str(tokens["access_token"]), current.slug)

        download = await api.get(f"/api/v1/files/{foreign_file}/download", headers=headers)
        assert download.status_code == 404
        assert "url" not in download.json()

        delete = await api.delete(f"/api/v1/files/{foreign_file}", headers=headers)
        assert delete.status_code == 404
    finally:
        await drop_tenant(other_slug, other_email)


async def test_quota_is_reserved_at_presign(
    api: AsyncClient,
    tenant: tuple[TenantContext, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current, owner_email = tenant
    monkeypatch.setattr(get_settings(), "quota_bytes", 1000)
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)

    first = await _presign(api, headers, filename="a.txt", content_type="text/plain", size=600)
    assert first.status_code == 200, first.text

    second = await _presign(api, headers, filename="b.txt", content_type="text/plain", size=600)
    assert second.status_code == 409
    assert second.json()["code"] == "quota_exceeded"


async def test_list_pagination_and_member_scope(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)
    owner_id = UUID(str((await api.get("/api/v1/users/me", headers=headers)).json()["id"]))
    for _ in range(3):
        await _insert_file(current, owner_id)

    suffix = current.slug.split("-", 1)[1]
    member_email = f"member-{suffix}@sehatbridge.dev"
    member_id = await _add_member(current, member_email, "member")
    await _insert_file(current, member_id)

    first = await api.get("/api/v1/files?limit=2", headers=headers)
    page1 = first.json()
    assert len(page1["items"]) == 2
    assert page1["has_more"] is True

    second = await api.get(f"/api/v1/files?limit=2&cursor={page1['next_cursor']}", headers=headers)
    page2 = second.json()
    ids = {item["id"] for item in page1["items"]} | {item["id"] for item in page2["items"]}
    assert len(ids) == 4
    assert page2["has_more"] is False

    member_tokens = await _login(api, current, member_email)
    member_headers = _auth(str(member_tokens["access_token"]), current.slug)
    member_list = await api.get("/api/v1/files", headers=member_headers)
    assert [item["owner_user_id"] for item in member_list.json()["items"]] == [str(member_id)]

    forbidden = await api.get(f"/api/v1/files?owner={owner_id}", headers=member_headers)
    assert forbidden.status_code == 403


async def test_bucket_cors_allows_site_origin(
    tenant: tuple[TenantContext, str],
) -> None:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        preflight = await client.options(
            f"{settings.minio_public_url}/{settings.minio_bucket}",
            headers={
                "Origin": settings.site_url,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert preflight.status_code in {200, 204}, preflight.text
    assert preflight.headers.get("access-control-allow-origin") == settings.site_url


async def test_sweeper_releases_expired_uploads(
    tenant: tuple[TenantContext, str],
) -> None:
    from app.files.sweep import sweep_expired

    current, _ = tenant
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        owner_id = await conn.fetchval(
            "SELECT user_id FROM public.memberships WHERE tenant_id = $1 LIMIT 1",
            current.id,
        )
    finally:
        await conn.close()

    file_id = await _insert_file(current, owner_id, status="uploading")
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('search_path', $1, true)",
                f"{schema_name(current.slug)}, public",
            )
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(current.id))
            await conn.execute(
                "UPDATE files SET created_at = now() - interval '20 minutes' WHERE id = $1",
                file_id,
            )
    finally:
        await conn.close()

    removed = await sweep_expired()
    assert removed >= 1

    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('search_path', $1, true)",
                f"{schema_name(current.slug)}, public",
            )
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(current.id))
            remaining = await conn.fetchval("SELECT 1 FROM files WHERE id = $1", file_id)
    finally:
        await conn.close()
    assert remaining is None
