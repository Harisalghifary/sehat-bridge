"""Credential management, sync enqueue, and job queries."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.config import get_settings
from app.db.tenant_context import TenantContext
from app.errors import AppError
from app.integrations.satusehat.crypto import get_secret_box
from app.integrations.satusehat.factory import base_url_for_mode, build_adapter
from app.integrations.satusehat.port import (
    Credentials,
    OrganizationDraft,
    PatientDraft,
)
from app.integrations.satusehat.schemas import (
    CredentialsIn,
    CredentialsOut,
    JobDetail,
    JobList,
    JobOut,
    SyncQueued,
    TestConnectionOut,
)
from app.pagination import decode_cursor, encode_cursor

SENSITIVE_KEYS = {
    "identifier",
    "nik",
    "name",
    "birthDate",
    "address",
    "telecom",
    "text",
}


def redact_body(value: Any) -> Any:
    """Strip identifiers before a response body is persisted or returned."""
    if isinstance(value, dict):
        return {
            key: "[redacted]" if key in SENSITIVE_KEYS else redact_body(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_body(item) for item in value]
    return value


def scrub_text(value: str, secret: str | None) -> str:
    if secret:
        value = value.replace(secret, "***")
    return value[:500]


def credentials_out(row: Any) -> CredentialsOut:
    settings = get_settings()
    return CredentialsOut(
        provider=row["provider"],
        status=row["status"],
        has_secret=bool(row["client_secret_enc"]),
        client_id=row["client_id"],
        organization_id=row["organization_id"],
        base_url=row["base_url"],
        last_verified_at=row["last_verified_at"],
        last_error=row["last_error"],
        mode=settings.satusehat_mode,
    )


async def get_credentials(session: AsyncSession) -> Any:
    return (
        (
            await session.execute(
                text("SELECT * FROM integration_credentials WHERE provider = 'satusehat'")
            )
        )
        .mappings()
        .first()
    )


async def upsert_credentials(
    session: AsyncSession,
    tenant: TenantContext,
    body: CredentialsIn,
    *,
    actor_id: UUID,
    ip: str | None,
) -> CredentialsOut:
    client_id = body.client_id.strip()
    organization_id = body.organization_id.strip()
    if not client_id or not organization_id:
        raise AppError(
            status=422,
            code="invalid_credentials_shape",
            title="Client id and organization id are required",
        )

    existing = await get_credentials(session)
    secret = body.client_secret.strip()
    if secret:
        encrypted = get_secret_box().encrypt(secret)
    elif existing is not None:
        encrypted = existing["client_secret_enc"]
    else:
        raise AppError(
            status=422,
            code="invalid_credentials_shape",
            title="A client secret is required",
        )

    row = (
        (
            await session.execute(
                text(
                    """
                INSERT INTO integration_credentials
                    (provider, client_id, client_secret_enc, organization_id,
                     base_url, status, last_error, last_verified_at, updated_at)
                VALUES
                    ('satusehat', :client_id, :secret, :organization_id,
                     :base_url, 'unverified', NULL, NULL, now())
                ON CONFLICT (provider) DO UPDATE SET
                    client_id = EXCLUDED.client_id,
                    client_secret_enc = EXCLUDED.client_secret_enc,
                    organization_id = EXCLUDED.organization_id,
                    base_url = EXCLUDED.base_url,
                    status = 'unverified',
                    last_error = NULL,
                    last_verified_at = NULL,
                    updated_at = now()
                RETURNING *
                """
                ),
                {
                    "client_id": client_id,
                    "secret": encrypted,
                    "organization_id": organization_id,
                    "base_url": base_url_for_mode(),
                },
            )
        )
        .mappings()
        .one()
    )

    await write_audit(
        session,
        "integration.credentials_updated",
        tenant_id=tenant.id,
        actor_user_id=actor_id,
        ip=ip,
        metadata={
            "provider": "satusehat",
            "organization_id": organization_id,
            "mode": get_settings().satusehat_mode,
        },
    )
    return credentials_out(row)


async def test_connection(
    session: AsyncSession,
    tenant: TenantContext,
    *,
    redis: Any,
    actor_id: UUID,
    ip: str | None,
) -> TestConnectionOut:
    row = await get_credentials(session)
    if row is None:
        raise AppError(
            status=404,
            code="credentials_not_found",
            title="SATUSEHAT credentials are not configured",
        )

    secret: str | None = None
    started = time.perf_counter()
    try:
        secret = get_secret_box().decrypt(row["client_secret_enc"])
        creds = Credentials(
            client_id=row["client_id"],
            client_secret=secret,
            base_url=row["base_url"],
        )
        adapter = build_adapter(redis, base_url=creds.base_url)
        token = await adapter.issue_token(creds)
        await adapter.get_resource(token, "Organization", row["organization_id"])
    except Exception as exc:
        message = scrub_text(str(exc) or exc.__class__.__name__, secret)
        await session.execute(
            text(
                """
                UPDATE integration_credentials
                   SET status = 'error', last_error = :error, updated_at = now()
                 WHERE provider = 'satusehat'
                """
            ),
            {"error": message},
        )
        await write_audit(
            session,
            "integration.connection_tested",
            tenant_id=tenant.id,
            actor_user_id=actor_id,
            ip=ip,
            metadata={"provider": "satusehat", "status": "error"},
        )
        return TestConnectionOut(status="error", error=message)

    latency_ms = int((time.perf_counter() - started) * 1000)
    await session.execute(
        text(
            """
            UPDATE integration_credentials
               SET status = 'connected', last_error = NULL,
                   last_verified_at = now(), updated_at = now()
             WHERE provider = 'satusehat'
            """
        )
    )
    await write_audit(
        session,
        "integration.connection_tested",
        tenant_id=tenant.id,
        actor_user_id=actor_id,
        ip=ip,
        metadata={
            "provider": "satusehat",
            "status": "connected",
            "latency_ms": latency_ms,
        },
    )
    return TestConnectionOut(status="connected", latency_ms=latency_ms)


def build_payload(kind: str, tenant: TenantContext, organization_id: str | None) -> dict[str, Any]:
    if kind == "organization":
        return {
            "resourceType": "Organization",
            "local_id": str(tenant.id),
            "identifier": organization_id,
            "name": tenant.name,
            "active": True,
        }
    # Synthetic demo patient: no NIK, no real patient data.
    identifier = f"sb-demo-{tenant.id.hex[:12]}"
    return {
        "resourceType": "Patient",
        "local_id": str(tenant.id),
        "identifier": identifier,
        "display_name": "Pasien Demo",
        "active": True,
    }


async def enqueue_sync(
    session: AsyncSession,
    tenant: TenantContext,
    *,
    kind: str,
    actor_id: UUID,
    ip: str | None,
) -> SyncQueued:
    row = await get_credentials(session)
    if row is None or row["status"] != "connected" or not row["organization_id"]:
        raise AppError(
            status=409,
            code="credentials_not_verified",
            title="Test the SATUSEHAT connection before syncing",
        )

    mapping = (
        await session.execute(
            text(
                """
                SELECT fhir_id FROM sync_resources
                 WHERE kind = :kind AND local_id = :local_id
                """
            ),
            {"kind": kind, "local_id": tenant.id},
        )
    ).first()
    if mapping is not None:
        latest = (
            await session.execute(
                text(
                    """
                    SELECT id, status FROM sync_jobs
                     WHERE kind = :kind AND local_id = :local_id
                     ORDER BY created_at DESC LIMIT 1
                    """
                ),
                {"kind": kind, "local_id": tenant.id},
            )
        ).first()
        if latest is not None:
            return SyncQueued(job_id=latest[0], status=latest[1])

    active = (
        await session.execute(
            text(
                """
                SELECT 1 FROM sync_jobs
                 WHERE kind = :kind AND local_id = :local_id
                   AND status IN ('queued', 'running')
                """
            ),
            {"kind": kind, "local_id": tenant.id},
        )
    ).first()
    if active is not None:
        raise AppError(
            status=409,
            code="sync_already_queued",
            title="A sync for this resource is already queued",
        )

    payload = build_payload(kind, tenant, row["organization_id"])
    try:
        job = (
            await session.execute(
                text(
                    """
                    INSERT INTO sync_jobs (tenant_id, kind, local_id, payload)
                    VALUES (:tenant_id, :kind, :local_id,
                            CAST(:payload AS jsonb))
                    RETURNING id, status
                    """
                ),
                {
                    "tenant_id": tenant.id,
                    "kind": kind,
                    "local_id": tenant.id,
                    "payload": json.dumps(payload),
                },
            )
        ).one()
    except IntegrityError as exc:
        raise AppError(
            status=409,
            code="sync_already_queued",
            title="A sync for this resource is already queued",
        ) from exc

    await write_audit(
        session,
        "integration.sync_queued",
        tenant_id=tenant.id,
        actor_user_id=actor_id,
        ip=ip,
        metadata={"provider": "satusehat", "kind": kind, "job_id": str(job.id)},
    )
    return SyncQueued(job_id=job.id, status=job.status)


JOB_COLUMNS = """
    j.id, j.kind, j.status, j.attempts, j.last_error,
    j.created_at, j.updated_at, m.fhir_id
"""


def job_out(row: Any) -> JobOut:
    return JobOut(
        id=row["id"],
        kind=row["kind"],
        status=row["status"],
        attempts=row["attempts"],
        last_error=row["last_error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        fhir_id=row["fhir_id"],
    )


async def list_jobs(session: AsyncSession, *, limit: int, cursor: str | None) -> JobList:
    params: dict[str, Any] = {"limit": limit + 1}
    condition = ""
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)
        condition = "AND (j.created_at, j.id) < (:cursor_ts, :cursor_id)"
        params["cursor_ts"] = cursor_ts
        params["cursor_id"] = cursor_id

    query = f"""
        SELECT {JOB_COLUMNS}
          FROM sync_jobs j
          LEFT JOIN sync_resources m
            ON m.kind = j.kind AND m.local_id = j.local_id
         WHERE true {condition}
         ORDER BY j.created_at DESC, j.id DESC
         LIMIT :limit
    """  # noqa: S608 - condition is a fixed internal fragment
    rows = (await session.execute(text(query), params)).mappings().all()

    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if has_more and page:
        next_cursor = encode_cursor(page[-1]["created_at"], page[-1]["id"])
    return JobList(
        items=[job_out(row) for row in page],
        next_cursor=next_cursor,
        has_more=has_more,
    )


async def get_job(session: AsyncSession, job_id: UUID) -> JobDetail:
    row = (
        (
            await session.execute(
                text(
                    f"""
                SELECT {JOB_COLUMNS}, j.response_body
                  FROM sync_jobs j
                  LEFT JOIN sync_resources m
                    ON m.kind = j.kind AND m.local_id = j.local_id
                 WHERE j.id = :job_id
                """  # noqa: S608 - column list is a module constant
                ),
                {"job_id": job_id},
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise AppError(status=404, code="job_not_found", title="Sync job not found")
    return JobDetail(
        **job_out(row).model_dump(),
        response_body=row["response_body"],
    )


def build_drafts(payload: dict[str, Any], local_id: UUID) -> OrganizationDraft | PatientDraft:
    if payload.get("resourceType") == "Organization":
        return OrganizationDraft(
            local_id=local_id,
            name=str(payload["name"]),
            identifier=str(payload["identifier"]),
        )
    return PatientDraft(
        local_id=local_id,
        identifier=str(payload["identifier"]),
        display_name=str(payload.get("display_name") or "Pasien Demo"),
    )
