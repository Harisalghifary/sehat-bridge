"""SATUSEHAT integration endpoints (per tenant, admin+)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthUser, require_role, tenant_db
from app.auth.rate_limit import client_ip
from app.db.tenant_context import TenantContext
from app.errors import AppError
from app.integrations.satusehat import service
from app.integrations.satusehat.schemas import (
    CredentialsIn,
    CredentialsOut,
    JobDetail,
    JobList,
    SyncQueued,
    SyncRequest,
    TestConnectionOut,
)

router = APIRouter(prefix="/api/v1/integrations/satusehat", tags=["integrations"])


def _tenant(user: AuthUser) -> TenantContext:
    if user.tenant is None:
        raise AppError(status=403, code="tenant_required", title="A tenant is required")
    return user.tenant


@router.get("", response_model=CredentialsOut, summary="Get SATUSEHAT configuration")
async def get_integration(
    user: AuthUser = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(tenant_db),
) -> CredentialsOut:
    row = await service.get_credentials(session)
    if row is None:
        raise AppError(
            status=404,
            code="credentials_not_found",
            title="SATUSEHAT credentials are not configured",
        )
    return service.credentials_out(row)


@router.put("", response_model=CredentialsOut, summary="Store SATUSEHAT credentials")
async def put_integration(
    body: CredentialsIn,
    request: Request,
    user: AuthUser = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(tenant_db),
) -> CredentialsOut:
    return await service.upsert_credentials(
        session,
        _tenant(user),
        body,
        actor_id=user.id,
        ip=client_ip(request),
    )


@router.post(
    "/test",
    response_model=TestConnectionOut,
    summary="Test credentials against the configured adapter",
)
async def test_integration(
    request: Request,
    user: AuthUser = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(tenant_db),
) -> TestConnectionOut:
    return await service.test_connection(
        session,
        _tenant(user),
        redis=request.app.state.redis,
        actor_id=user.id,
        ip=client_ip(request),
    )


@router.post(
    "/sync",
    response_model=SyncQueued,
    status_code=202,
    summary="Queue a resource sync",
)
async def sync(
    body: SyncRequest,
    request: Request,
    user: AuthUser = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(tenant_db),
) -> SyncQueued:
    return await service.enqueue_sync(
        session,
        _tenant(user),
        kind=body.kind,
        actor_id=user.id,
        ip=client_ip(request),
    )


@router.get("/jobs", response_model=JobList, summary="List sync jobs")
async def jobs(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    user: AuthUser = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(tenant_db),
) -> JobList:
    return await service.list_jobs(session, limit=limit, cursor=cursor)


@router.get("/jobs/{job_id}", response_model=JobDetail, summary="Get a sync job")
async def job(
    job_id: UUID,
    user: AuthUser = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(tenant_db),
) -> JobDetail:
    return await service.get_job(session, job_id)
