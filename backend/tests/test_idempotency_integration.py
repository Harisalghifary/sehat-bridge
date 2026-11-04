"""Idempotency replay returns the original response and creates one row."""

from __future__ import annotations

import uuid

import asyncpg
import pytest
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import TenantContext, schema_name
from httpx import AsyncClient

from tests.conftest import PASSWORD

pytestmark = pytest.mark.integration


async def _login(api: AsyncClient, slug: str, email: str) -> str:
    response = await api.post(
        "/api/v1/auth/login",
        json={"tenant_slug": slug, "email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def test_presign_replay_creates_one_row(
    api: AsyncClient, tenant: tuple[TenantContext, str]
) -> None:
    current, email = tenant
    token = await _login(api, current.slug, email)
    headers = {
        "authorization": f"Bearer {token}",
        "x-tenant-id": current.slug,
        "idempotency-key": str(uuid.uuid4()),
    }
    body = {"filename": "replay.txt", "size_bytes": 12, "content_type": "text/plain"}

    first = await api.post("/api/v1/files/presign-upload", headers=headers, json=body)
    second = await api.post("/api/v1/files/presign-upload", headers=headers, json=body)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()
    assert second.headers.get("idempotency-replayed") == "true"

    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        count = await conn.fetchval(
            f'SELECT count(*) FROM "{schema_name(current.slug)}".files '  # noqa: S608
            "WHERE filename = 'replay.txt'"
        )
    finally:
        await conn.close()
    assert count == 1

    changed = await api.post(
        "/api/v1/files/presign-upload",
        headers=headers,
        json={**body, "filename": "different.txt"},
    )
    assert changed.status_code == 422
    assert changed.json()["code"] == "idempotency_key_reuse"
