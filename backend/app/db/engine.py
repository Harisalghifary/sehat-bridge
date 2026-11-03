"""Async engine and session factories.

Two URLs, on purpose:
- ``migration_database_url`` connects as the schema owner; only provisioning and
  migrations use it.
- ``database_url`` connects as the non-owner app role, so RLS policies apply.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def asyncpg_dsn(url: str) -> str:
    """Strip the SQLAlchemy driver prefix for a raw asyncpg connection."""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def make_engine(url: str, *, pool_size: int = 5) -> AsyncEngine:
    return create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=pool_size,
        # Tenant schemas are created and dropped at runtime; asyncpg's prepared
        # statement cache considers those plans invalid. Disable it so a
        # provision/drop does not poison pooled connections.
        connect_args={"statement_cache_size": 0},
    )


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
