"""SATUSEHAT pipeline: credentials, test connection, outbox, retries, isolation."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import asyncpg
import pytest
from app.auth.security import hash_password
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import TenantContext, schema_name
from app.integrations.satusehat.crypto import SecretBox
from app.integrations.satusehat.mock import deterministic_id
from app.integrations.satusehat.worker import run_worker
from app.tenancy import service
from httpx import AsyncClient

from tests.conftest import PASSWORD, drop_tenant

pytestmark = pytest.mark.integration

ORG_ID = "1000000001"


@asynccontextmanager
async def tenant_conn(tenant: TenantContext) -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('search_path', $1, true)",
                f"{schema_name(tenant.slug)}, public",
            )
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant.id))
            yield conn
    finally:
        await conn.close()


async def _login(api: AsyncClient, tenant: TenantContext, email: str) -> dict[str, Any]:
    response = await api.post(
        "/api/v1/auth/login",
        json={"tenant_slug": tenant.slug, "email": email, "password": PASSWORD},
        headers={"X-Forwarded-For": f"10.{uuid.uuid4().int % 250}.3.1"},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def _auth(token: str, slug: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": slug}


async def _put_credentials(api: AsyncClient, headers: dict[str, str], secret: str) -> Any:
    return await api.put(
        "/api/v1/integrations/satusehat",
        headers=headers,
        json={
            "client_id": "client-id",
            "client_secret": secret,
            "organization_id": ORG_ID,
        },
    )


async def _configure_and_test(
    api: AsyncClient, current: TenantContext, owner_email: str
) -> tuple[dict[str, str], str]:
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)
    secret = f"secret-{uuid.uuid4().hex}"
    saved = await _put_credentials(api, headers, secret)
    assert saved.status_code == 200, saved.text
    tested = await api.post("/api/v1/integrations/satusehat/test", headers=headers)
    assert tested.status_code == 200, tested.text
    assert tested.json()["status"] == "connected", tested.text
    return headers, secret


async def _set_base_url(tenant: TenantContext, base_url: str) -> None:
    async with tenant_conn(tenant) as conn:
        await conn.execute(
            "UPDATE integration_credentials SET base_url = $1 WHERE provider = 'satusehat'",
            base_url,
        )


async def _set_running(tenant: TenantContext, job_id: str) -> None:
    async with tenant_conn(tenant) as conn:
        await conn.execute(
            """
            UPDATE sync_jobs
               SET status = 'running', attempts = 1,
                   updated_at = now() - interval '10 minutes'
             WHERE id = $1
            """,
            UUID(job_id),
        )


async def test_credentials_are_write_only_and_encrypted(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)
    secret = f"ultra-secret-{uuid.uuid4().hex}"

    saved = await _put_credentials(api, headers, secret)
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "unverified"
    assert saved.json()["has_secret"] is True
    assert secret not in saved.text

    fetched = await api.get("/api/v1/integrations/satusehat", headers=headers)
    assert fetched.status_code == 200
    assert secret not in fetched.text
    assert fetched.json()["has_secret"] is True

    async with tenant_conn(current) as conn:
        ciphertext = await conn.fetchval(
            "SELECT client_secret_enc FROM integration_credentials WHERE provider = 'satusehat'"
        )
        audit = await conn.fetchval(
            """
            SELECT metadata::text FROM public.audit_log
             WHERE tenant_id = $1
               AND action = 'integration.credentials_updated'
             ORDER BY created_at DESC LIMIT 1
            """,
            current.id,
        )
    assert secret.encode() not in bytes(ciphertext)
    assert SecretBox(get_settings().app_encryption_key).decrypt(ciphertext) == secret
    assert secret not in (audit or "")
    assert "organization_id" in json.loads(audit)


async def test_test_connection_transitions_status(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)
    saved = await _put_credentials(api, headers, "secret-value")
    assert saved.status_code == 200

    tested = await api.post("/api/v1/integrations/satusehat/test", headers=headers)
    assert tested.status_code == 200
    assert tested.json()["status"] == "connected"
    assert tested.json()["latency_ms"] is not None

    fetched = await api.get("/api/v1/integrations/satusehat", headers=headers)
    assert fetched.json()["status"] == "connected"
    assert fetched.json()["last_verified_at"] is not None

    # Rotating credentials resets verification and blocks sync.
    rotated = await _put_credentials(api, headers, "another-secret")
    assert rotated.json()["status"] == "unverified"
    blocked = await api.post(
        "/api/v1/integrations/satusehat/sync",
        headers=headers,
        json={"kind": "organization"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "credentials_not_verified"


async def test_failed_connection_reports_error_without_raising(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    tokens = await _login(api, current, owner_email)
    headers = _auth(str(tokens["access_token"]), current.slug)
    await _put_credentials(api, headers, "secret-value")
    await _set_base_url(current, "http://localhost:8090/fhir-r4/v1?fail=4xx")

    tested = await api.post("/api/v1/integrations/satusehat/test", headers=headers)
    assert tested.status_code == 200
    assert tested.json()["status"] == "error"
    assert tested.json()["error"]

    fetched = await api.get("/api/v1/integrations/satusehat", headers=headers)
    assert fetched.json()["status"] == "error"


async def test_sync_organization_is_idempotent(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    headers, _ = await _configure_and_test(api, current, owner_email)

    queued = await api.post(
        "/api/v1/integrations/satusehat/sync",
        headers=headers,
        json={"kind": "organization"},
    )
    assert queued.status_code == 202, queued.text
    job_id = UUID(queued.json()["job_id"])
    assert queued.json()["status"] == "queued"

    processed = await run_worker(once=True)
    assert processed >= 1

    detail = await api.get(f"/api/v1/integrations/satusehat/jobs/{job_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    job = detail.json()
    expected = deterministic_id("Organization", ORG_ID)
    assert job["status"] == "done"
    assert job["attempts"] == 1
    assert job["fhir_id"] == expected

    again = await api.post(
        "/api/v1/integrations/satusehat/sync",
        headers=headers,
        json={"kind": "organization"},
    )
    assert again.status_code == 202
    assert again.json()["job_id"] == str(job_id)

    async with tenant_conn(current) as conn:
        count = await conn.fetchval("SELECT count(*) FROM sync_jobs WHERE kind = 'organization'")
        mapping = await conn.fetchval(
            "SELECT fhir_id FROM sync_resources WHERE kind = 'organization'"
        )
    assert count == 1
    assert mapping == expected

    listing = await api.get("/api/v1/integrations/satusehat/jobs", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["items"][0]["fhir_id"] == expected


async def test_patient_sync_uses_synthetic_identifier(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    headers, _ = await _configure_and_test(api, current, owner_email)

    queued = await api.post(
        "/api/v1/integrations/satusehat/sync",
        headers=headers,
        json={"kind": "patient"},
    )
    assert queued.status_code == 202, queued.text
    job_id = queued.json()["job_id"]
    await run_worker(once=True)

    detail = (
        await api.get(f"/api/v1/integrations/satusehat/jobs/{job_id}", headers=headers)
    ).json()
    assert detail["status"] == "done"
    expected = deterministic_id("Patient", f"sb-demo-{current.id.hex[:12]}")
    assert detail["fhir_id"] == expected


async def test_retryable_failure_retries_then_dies(
    api: AsyncClient,
    tenant: tuple[TenantContext, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    current, owner_email = tenant
    headers, secret = await _configure_and_test(api, current, owner_email)
    await _set_base_url(current, "http://localhost:8090/fhir-r4/v1?fail=500")
    monkeypatch.setattr(get_settings(), "satusehat_backoff_base_seconds", 0.0)
    monkeypatch.setattr(get_settings(), "satusehat_max_attempts", 3)

    queued = await api.post(
        "/api/v1/integrations/satusehat/sync",
        headers=headers,
        json={"kind": "organization"},
    )
    job_id = queued.json()["job_id"]

    with caplog.at_level(logging.INFO):
        for _ in range(3):
            await run_worker(once=True)

    detail = (
        await api.get(f"/api/v1/integrations/satusehat/jobs/{job_id}", headers=headers)
    ).json()
    assert detail["status"] == "dead"
    assert detail["attempts"] == 3
    assert "500" in (detail["last_error"] or "")
    assert detail["response_body"] is not None
    assert secret not in json.dumps(detail)
    assert secret not in caplog.text

    await run_worker(once=True)
    unchanged = (
        await api.get(f"/api/v1/integrations/satusehat/jobs/{job_id}", headers=headers)
    ).json()
    assert unchanged["attempts"] == 3


async def test_terminal_4xx_fails_without_retry(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    headers, _ = await _configure_and_test(api, current, owner_email)
    await _set_base_url(current, "http://localhost:8090/fhir-r4/v1?fail=4xx")

    queued = await api.post(
        "/api/v1/integrations/satusehat/sync",
        headers=headers,
        json={"kind": "organization"},
    )
    job_id = queued.json()["job_id"]

    await run_worker(once=True)
    detail = (
        await api.get(f"/api/v1/integrations/satusehat/jobs/{job_id}", headers=headers)
    ).json()
    assert detail["status"] == "failed"
    assert detail["attempts"] == 1

    await run_worker(once=True)
    unchanged = (
        await api.get(f"/api/v1/integrations/satusehat/jobs/{job_id}", headers=headers)
    ).json()
    assert unchanged["attempts"] == 1


async def test_cross_tenant_jobs_and_credentials_are_invisible(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, owner_email = tenant
    headers, _ = await _configure_and_test(api, current, owner_email)
    queued = await api.post(
        "/api/v1/integrations/satusehat/sync",
        headers=headers,
        json={"kind": "organization"},
    )
    job_id = queued.json()["job_id"]

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
        other_tokens = await _login(api, other, other_email)
        other_headers = _auth(str(other_tokens["access_token"]), other.slug)

        job = await api.get(f"/api/v1/integrations/satusehat/jobs/{job_id}", headers=other_headers)
        assert job.status_code == 404

        creds = await api.get("/api/v1/integrations/satusehat", headers=other_headers)
        assert creds.status_code == 404
        assert creds.json()["code"] == "credentials_not_found"
    finally:
        await drop_tenant(other_slug, other_email)


async def test_running_job_is_recovered_after_worker_restart(
    api: AsyncClient,
    tenant: tuple[TenantContext, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current, owner_email = tenant
    headers, _ = await _configure_and_test(api, current, owner_email)
    queued = await api.post(
        "/api/v1/integrations/satusehat/sync",
        headers=headers,
        json={"kind": "organization"},
    )
    job_id = queued.json()["job_id"]
    await _set_running(current, job_id)
    monkeypatch.setattr(get_settings(), "worker_stale_seconds", 0)

    await run_worker(once=True)

    detail = (
        await api.get(f"/api/v1/integrations/satusehat/jobs/{job_id}", headers=headers)
    ).json()
    assert detail["status"] == "done"
    assert detail["attempts"] == 2
