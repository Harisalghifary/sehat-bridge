"""Append-only audit writes shared by auth and user management."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def write_audit(
    session: AsyncSession,
    action: str,
    *,
    tenant_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    ip: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO public.audit_log
                (tenant_id, actor_user_id, action, metadata, ip)
            VALUES (
                :tenant_id, :actor, :action,
                CAST(:metadata AS jsonb), CAST(:ip AS inet)
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "actor": actor_user_id,
            "action": action,
            "metadata": json.dumps(metadata or {}),
            "ip": ip,
        },
    )
