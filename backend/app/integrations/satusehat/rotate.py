"""Re-wrap all tenant integration secrets under a new encryption key."""

from __future__ import annotations

import asyncpg

from app.config import get_settings
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import schema_name
from app.integrations.satusehat.crypto import SecretBox


async def rewrap_secrets(old_key: str, *, slugs: list[str] | None = None) -> int:
    settings = get_settings()
    new_box = SecretBox(settings.app_encryption_key)
    old_box = SecretBox(old_key)
    conn = await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))
    try:
        if slugs:
            rows = await conn.fetch(
                "SELECT slug FROM public.tenants "
                "WHERE status = 'active' AND slug = ANY($1::citext[]) ORDER BY slug",
                slugs,
            )
        else:
            rows = await conn.fetch(
                "SELECT slug FROM public.tenants WHERE status = 'active' ORDER BY slug"
            )
        pending: list[tuple[str, bytes]] = []
        for row in rows:
            schema = schema_name(row["slug"])
            exists = await conn.fetchval(
                "SELECT to_regclass($1) IS NOT NULL", f"{schema}.integration_credentials"
            )
            if not exists:
                continue
            creds = await conn.fetch(
                f'SELECT provider, client_secret_enc FROM "{schema}".integration_credentials'  # noqa: S608
            )
            for cred in creds:
                plaintext = old_box.decrypt(cred["client_secret_enc"])
                pending.append((f"{schema}.{cred['provider']}", new_box.encrypt(plaintext)))

        async with conn.transaction():
            for key, encrypted in pending:
                schema, provider = key.rsplit(".", 1)
                await conn.execute(
                    f'UPDATE "{schema}".integration_credentials '  # noqa: S608
                    "SET client_secret_enc = $1, updated_at = now() "
                    "WHERE provider = $2",
                    encrypted,
                    provider,
                )
        return len(pending)
    finally:
        await conn.close()
