"""Encryption-key rotation re-wraps stored tenant secrets."""

from __future__ import annotations

import asyncpg
import pytest
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import TenantContext, schema_name
from app.integrations.satusehat.crypto import InvalidToken, SecretBox
from app.integrations.satusehat.rotate import rewrap_secrets
from httpx import AsyncClient

from tests.conftest import PASSWORD

pytestmark = pytest.mark.integration


async def test_rewrap_moves_secret_to_new_key(
    api: AsyncClient,
    tenant: tuple[TenantContext, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current, email = tenant
    login = await api.post(
        "/api/v1/auth/login",
        json={"tenant_slug": current.slug, "email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    secret = "super-secret-value-123"
    stored = await api.put(
        "/api/v1/integrations/satusehat",
        headers={
            "authorization": f"Bearer {token}",
            "x-tenant-id": current.slug,
        },
        json={
            "client_id": "client-id",
            "client_secret": secret,
            "organization_id": "org-id",
        },
    )
    assert stored.status_code == 200, stored.text

    old_key = get_settings().app_encryption_key
    new_key = "rotated-encryption-key-000000000000"
    monkeypatch.setattr(
        "app.integrations.satusehat.rotate.get_settings",
        lambda: get_settings().model_copy(update={"app_encryption_key": new_key}),
    )

    count = await rewrap_secrets(old_key, slugs=[current.slug])
    assert count == 1

    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        encrypted = await conn.fetchval(
            f'SELECT client_secret_enc FROM "{schema_name(current.slug)}"'  # noqa: S608
            ".integration_credentials WHERE provider = 'satusehat'"
        )
    finally:
        await conn.close()

    assert SecretBox(new_key).decrypt(encrypted) == secret
    with pytest.raises(InvalidToken):
        SecretBox(old_key).decrypt(encrypted)
