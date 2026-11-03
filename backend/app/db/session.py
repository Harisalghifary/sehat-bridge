"""Session helpers that enforce tenant isolation.

``set_config(..., is_local => true)`` is used instead of ``SET LOCAL`` so the
value is bound as a parameter rather than interpolated into SQL. Both are
transaction-scoped: the connection returns to the pool clean.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.tenant_context import TenantContext


@asynccontextmanager
async def public_session(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        async with session.begin():
            yield session


@asynccontextmanager
async def tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    tenant: TenantContext,
) -> AsyncIterator[AsyncSession]:
    """Open a transaction bound to one tenant's schema and identity."""
    async with sessionmaker() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('search_path', :path, true)"),
                {"path": f"{tenant.schema}, public"},
            )
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant.id)},
            )
            yield session
