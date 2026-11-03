"""Outbox worker: fair, resumable, bounded retries.

The worker is a separate process (``make worker``). It claims at most one job
per tenant per cycle so a poisoned tenant cannot starve the rest, and it never
holds a database transaction open across a network call.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit import write_audit
from app.config import Settings, get_settings
from app.db.engine import make_engine, make_sessionmaker
from app.db.session import tenant_session
from app.db.tenant_context import TenantContext
from app.errors import AppError
from app.integrations.satusehat import service
from app.integrations.satusehat.crypto import InvalidToken, get_secret_box
from app.integrations.satusehat.factory import build_adapter
from app.integrations.satusehat.port import (
    Credentials,
    OrganizationDraft,
    SatusehatError,
)
from app.tenancy import service as tenancy_service

logger = logging.getLogger(__name__)


async def _tenant_contexts(engine: Any) -> list[TenantContext]:
    contexts: list[TenantContext] = []
    for slug, _name, status in await tenancy_service.list_tenants():
        if status != "active":
            continue
        tenant = await tenancy_service.get_tenant_by_slug(engine, slug)
        if tenant is not None:
            contexts.append(tenant)
    return contexts


async def recover_stale_jobs(
    sessionmaker: async_sessionmaker[AsyncSession],
    tenant: TenantContext,
    *,
    stale_seconds: int,
) -> int:
    """Requeue jobs left ``running`` by a killed worker."""
    async with tenant_session(sessionmaker, tenant) as session:
        result = await session.execute(
            text(
                """
                UPDATE sync_jobs
                   SET status = 'queued',
                       next_attempt_at = now(),
                       updated_at = now()
                 WHERE status = 'running'
                   AND updated_at < now() - (CAST(:stale AS integer)
                                             * interval '1 second')
                """
            ),
            {"stale": stale_seconds},
        )
        return int(getattr(result, "rowcount", 0) or 0)


async def _claim(
    sessionmaker: async_sessionmaker[AsyncSession], tenant: TenantContext
) -> dict[str, Any] | None:
    async with tenant_session(sessionmaker, tenant) as session:
        row = (
            (
                await session.execute(
                    text(
                        """
                    SELECT id, kind, local_id, payload, attempts
                      FROM sync_jobs
                     WHERE status = 'queued' AND next_attempt_at <= now()
                     ORDER BY next_attempt_at, created_at
                     FOR UPDATE SKIP LOCKED
                     LIMIT 1
                    """
                    )
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        claimed = (
            (
                await session.execute(
                    text(
                        """
                    UPDATE sync_jobs
                       SET status = 'running', attempts = attempts + 1,
                           updated_at = now()
                     WHERE id = :id
                 RETURNING attempts
                    """
                    ),
                    {"id": row["id"]},
                )
            )
            .mappings()
            .one()
        )
        job = dict(row)
        job["attempts"] = claimed["attempts"]
    payload = job["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    job["payload"] = payload
    return job


async def _load_credentials(session: AsyncSession) -> tuple[Any, str] | None:
    row = await service.get_credentials(session)
    if row is None:
        return None
    secret = get_secret_box().decrypt(row["client_secret_enc"])
    return row, secret


async def _mark_done(
    sessionmaker: async_sessionmaker[AsyncSession],
    tenant: TenantContext,
    job: dict[str, Any],
    fhir_id: str,
    fhir_type: str,
) -> None:
    async with tenant_session(sessionmaker, tenant) as session:
        await session.execute(
            text(
                """
                UPDATE sync_jobs
                   SET status = 'done', last_error = NULL,
                       response_body = NULL, updated_at = now()
                 WHERE id = :id
                """
            ),
            {"id": job["id"]},
        )
        await session.execute(
            text(
                """
                INSERT INTO sync_resources (kind, local_id, fhir_id, fhir_type)
                VALUES (:kind, :local_id, :fhir_id, :fhir_type)
                ON CONFLICT (kind, local_id) DO UPDATE SET
                    fhir_id = EXCLUDED.fhir_id,
                    fhir_type = EXCLUDED.fhir_type,
                    synced_at = now()
                """
            ),
            {
                "kind": job["kind"],
                "local_id": job["local_id"],
                "fhir_id": fhir_id,
                "fhir_type": fhir_type,
            },
        )
        await write_audit(
            session,
            "integration.sync_done",
            tenant_id=tenant.id,
            metadata={
                "job_id": str(job["id"]),
                "kind": job["kind"],
                "fhir_id": fhir_id,
            },
        )


async def _mark_retry_or_fail(
    sessionmaker: async_sessionmaker[AsyncSession],
    tenant: TenantContext,
    job: dict[str, Any],
    *,
    message: str,
    retryable: bool,
    response_body: dict[str, Any] | None,
    settings: Settings,
) -> str:
    attempts = int(job["attempts"])
    if not retryable or attempts >= settings.satusehat_max_attempts:
        status = "failed" if not retryable else "dead"
        next_attempt: Any = None
    else:
        status = "queued"
        next_attempt = f"{settings.satusehat_backoff_base_seconds * (2 ** (attempts - 1))} seconds"

    async with tenant_session(sessionmaker, tenant) as session:
        await session.execute(
            text(
                """
                UPDATE sync_jobs
                   SET status = :status,
                       last_error = :error,
                       response_body = CAST(:body AS jsonb),
                       next_attempt_at = CASE
                           WHEN CAST(:next_attempt AS text) IS NULL THEN next_attempt_at
                           ELSE now() + CAST(:next_attempt AS interval)
                       END,
                       updated_at = now()
                 WHERE id = :id
                """
            ),
            {
                "status": status,
                "error": message,
                "body": json.dumps(response_body) if response_body else None,
                "next_attempt": next_attempt,
                "id": job["id"],
            },
        )
        if status in {"failed", "dead"}:
            await write_audit(
                session,
                "integration.sync_failed",
                tenant_id=tenant.id,
                metadata={
                    "job_id": str(job["id"]),
                    "kind": job["kind"],
                    "status": status,
                    "attempts": attempts,
                },
            )
    return status


async def _process_job(
    sessionmaker: async_sessionmaker[AsyncSession],
    tenant: TenantContext,
    job: dict[str, Any],
    *,
    redis: Redis,
    settings: Settings,
) -> None:
    async with tenant_session(sessionmaker, tenant) as session:
        mapping = (
            await session.execute(
                text(
                    "SELECT fhir_id, fhir_type FROM sync_resources"
                    " WHERE kind = :kind AND local_id = :local_id"
                ),
                {"kind": job["kind"], "local_id": job["local_id"]},
            )
        ).first()
        if mapping is not None:
            await session.execute(
                text(
                    "UPDATE sync_jobs SET status = 'done', last_error = NULL,"
                    " updated_at = now() WHERE id = :id"
                ),
                {"id": job["id"]},
            )
            return

        loaded = None
        try:
            loaded = await _load_credentials(session)
        except InvalidToken:
            await session.execute(
                text(
                    "UPDATE sync_jobs SET status = 'failed',"
                    " last_error = 'credential_decrypt_failed',"
                    " updated_at = now() WHERE id = :id"
                ),
                {"id": job["id"]},
            )
            return
        if loaded is None:
            await session.execute(
                text(
                    "UPDATE sync_jobs SET status = 'failed',"
                    " last_error = 'credentials_not_found', updated_at = now()"
                    " WHERE id = :id"
                ),
                {"id": job["id"]},
            )
            return
        creds_row, secret = loaded

    creds = Credentials(
        client_id=creds_row["client_id"],
        client_secret=secret,
        base_url=creds_row["base_url"],
    )
    payload = job["payload"]
    adapter = build_adapter(redis, base_url=creds.base_url)

    try:
        token = await adapter.issue_token(creds)
        draft = service.build_drafts(payload, UUID(str(job["local_id"])))
        if isinstance(draft, OrganizationDraft):
            ref = await adapter.put_organization(token, draft)
        else:
            ref = await adapter.put_patient(token, draft)
    except SatusehatError as exc:
        message = service.scrub_text(exc.message, secret)
        status = await _mark_retry_or_fail(
            sessionmaker,
            tenant,
            job,
            message=message,
            retryable=exc.retryable,
            response_body=(
                {
                    "error": message,
                    "status_code": exc.status_code,
                    "body": service.redact_body(exc.body),
                }
                if exc.body
                else None
            ),
            settings=settings,
        )
        logger.info(
            "job %s tenant=%s kind=%s status=%s attempts=%s",
            job["id"],
            tenant.slug,
            job["kind"],
            status,
            job["attempts"],
        )
        return
    except (InvalidToken, AppError) as exc:
        message = service.scrub_text(str(exc) or "credential_error", secret)
        await _mark_retry_or_fail(
            sessionmaker,
            tenant,
            job,
            message=message,
            retryable=False,
            response_body=None,
            settings=settings,
        )
        return
    except Exception as exc:
        message = service.scrub_text(f"{type(exc).__name__}: {exc}", secret)
        status = await _mark_retry_or_fail(
            sessionmaker,
            tenant,
            job,
            message=message,
            retryable=True,
            response_body=None,
            settings=settings,
        )
        logger.info(
            "job %s tenant=%s kind=%s status=%s attempts=%s",
            job["id"],
            tenant.slug,
            job["kind"],
            status,
            job["attempts"],
        )
        return

    await _mark_done(sessionmaker, tenant, job, ref.id, ref.resource_type)
    logger.info(
        "job %s tenant=%s kind=%s status=done attempts=%s",
        job["id"],
        tenant.slug,
        job["kind"],
        job["attempts"],
    )


async def run_worker(*, once: bool = False) -> int:
    settings = get_settings()
    engine = make_engine(settings.database_url, pool_size=2)
    sessionmaker = make_sessionmaker(engine)
    redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
    processed = 0
    start = 0
    try:
        tenants = await _tenant_contexts(engine)
        for tenant in tenants:
            await recover_stale_jobs(
                sessionmaker, tenant, stale_seconds=settings.worker_stale_seconds
            )
        if once:
            for tenant in tenants:
                job = await _claim(sessionmaker, tenant)
                if job is None:
                    continue
                await _process_job(sessionmaker, tenant, job, redis=redis, settings=settings)
                processed += 1
            return processed

        while True:
            tenants = await _tenant_contexts(engine)
            if not tenants:
                await asyncio.sleep(settings.worker_poll_seconds)
                continue
            start %= len(tenants)
            order = tenants[start:] + tenants[:start]
            worked = 0
            for tenant in order:
                job = await _claim(sessionmaker, tenant)
                if job is None:
                    continue
                await _process_job(sessionmaker, tenant, job, redis=redis, settings=settings)
                worked += 1
                processed += 1
            start = (start + 1) % len(tenants)
            if worked == 0:
                await asyncio.sleep(settings.worker_poll_seconds)
    finally:
        await redis.aclose()
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.integrations.satusehat.worker")
    parser.add_argument("--once", action="store_true", help="drain one pass and exit")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    processed = asyncio.run(run_worker(once=args.once))
    print(f"worker: processed {processed} job(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
