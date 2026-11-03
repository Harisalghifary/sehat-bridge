"""Release quota held by abandoned uploads.

An expired row is deleted (never completed, so no audit value) and its object is
removed. The operation is idempotent: deleting a missing object is a no-op.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from app.config import get_settings
from app.db.engine import make_engine, make_sessionmaker
from app.db.session import tenant_session
from app.storage import delete_object
from app.tenancy import service

logger = logging.getLogger(__name__)


async def sweep_expired() -> int:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    sessionmaker = make_sessionmaker(engine)
    removed = 0
    try:
        for slug, _name, status in await service.list_tenants():
            if status != "active":
                continue
            tenant = await service.get_tenant_by_slug(engine, slug)
            if tenant is None:
                continue
            async with tenant_session(sessionmaker, tenant) as session:
                rows = (
                    (
                        await session.execute(
                            text(
                                """
                            SELECT id, object_key FROM files
                             WHERE status = 'uploading'
                               AND created_at
                                   < now() - (CAST(:ttl AS integer)
                                              * interval '1 second')
                             FOR UPDATE
                            """
                            ),
                            {"ttl": settings.upload_url_ttl_seconds},
                        )
                    )
                    .mappings()
                    .all()
                )
                for row in rows:
                    await delete_object(row["object_key"])
                    await session.execute(
                        text("DELETE FROM files WHERE id = :id"),
                        {"id": row["id"]},
                    )
                    removed += 1
                    logger.info(
                        "sweep: removed expired upload %s (%s)",
                        row["id"],
                        row["object_key"],
                    )
    finally:
        await engine.dispose()
    return removed


def main() -> int:
    removed = asyncio.run(sweep_expired())
    print(f"sweep: removed {removed} expired upload(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
