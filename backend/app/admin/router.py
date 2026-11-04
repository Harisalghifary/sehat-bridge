"""Platform operator API: tenants, audit, and runtime health."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, status

from app.admin import service
from app.admin.schemas import (
    AuditList,
    AuditRow,
    OpsHealth,
    ProvisionRequest,
    ProvisionResponse,
    ProvisionStep,
    QueueDepth,
    TenantActionResponse,
    TenantCounts,
    TenantDetail,
    TenantList,
    TenantMigrationResult,
    TenantMigrationSummary,
    TenantRow,
)
from app.auth.dependencies import AuthUser, require_platform_admin
from app.auth.schemas import MeResponse
from app.auth.security import hash_password
from app.config import get_settings
from app.errors import AppError
from app.health import check_minio, check_postgres, check_redis
from app.tenancy import service as tenancy
from app.tenancy.service import ProvisioningError

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

Operator = Annotated[AuthUser, Depends(require_platform_admin)]


def _row(data: dict) -> TenantRow:
    return TenantRow(**data)


def _detail(data: dict) -> TenantDetail:
    return TenantDetail(**data)


@router.get("/me", response_model=MeResponse, summary="Current operator")
async def operator_me(user: Operator) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        is_verified=user.is_verified,
        is_platform_admin=user.is_platform_admin,
        membership=None,
        profile=None,
    )


@router.get("/tenants", response_model=TenantList, summary="List tenants")
async def list_tenants(_: Operator) -> TenantList:
    return TenantList(items=[_row(item) for item in await service.list_tenants_admin()])


@router.get("/tenants/{slug}", response_model=TenantDetail, summary="Tenant detail")
async def tenant_detail(slug: str, _: Operator) -> TenantDetail:
    data = await service.get_tenant_admin(slug)
    if data is None:
        raise AppError(status=404, code="tenant_not_found", title="Tenant not found")
    return _detail(data)


@router.post(
    "/tenants",
    response_model=ProvisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a tenant",
)
async def provision_tenant(body: ProvisionRequest, user: Operator) -> ProvisionResponse:
    existing = await service.get_tenant_admin(body.slug)
    if existing is not None:
        raise AppError(
            status=409,
            code="tenant_exists",
            title="Tenant already exists",
            detail=f"Tenant {body.slug} already exists.",
        )

    try:
        created = await tenancy.provision_tenant(
            slug=body.slug,
            name=body.name,
            owner_email=str(body.owner_email),
            owner_display_name=body.owner_display_name,
            password_hash=hash_password(body.password),
        )
    except ProvisioningError as exc:
        raise AppError(
            status=500,
            code="provisioning_failed",
            title="Tenant provisioning failed",
            detail=str(exc),
        ) from exc

    await service.record_audit(
        tenant_id=created.id,
        actor_user_id=user.id,
        action="tenant.provisioned_by_platform",
        resource_type="tenant",
        resource_id=created.slug,
        metadata={"owner_email": str(body.owner_email)},
    )
    data = await service.get_tenant_admin(created.slug)
    if data is None:
        raise AppError(status=500, code="provisioning_failed", title="Tenant not found")

    return ProvisionResponse(
        tenant=_detail(data),
        owner_email=str(body.owner_email),
        steps=[
            ProvisionStep(key="schema", label="Membuat skema tenant", status="done"),
            ProvisionStep(key="migrations", label="Menjalankan migrasi tenant", status="done"),
            ProvisionStep(key="owner", label="Menyiapkan akun owner", status="done"),
        ],
    )


@router.post(
    "/tenants/{slug}/suspend",
    response_model=TenantActionResponse,
    summary="Suspend a tenant",
)
async def suspend_tenant(slug: str, user: Operator) -> TenantActionResponse:
    return await _change_status(
        slug,
        user,
        target="suspended",
        audit_action="tenant.suspended",
        response_action="suspended",
    )


@router.post(
    "/tenants/{slug}/resume",
    response_model=TenantActionResponse,
    summary="Resume a tenant",
)
async def resume_tenant(slug: str, user: Operator) -> TenantActionResponse:
    return await _change_status(
        slug,
        user,
        target="active",
        audit_action="tenant.resumed",
        response_action="resumed",
    )


async def _change_status(
    slug: str,
    user: AuthUser,
    *,
    target: Literal["suspended", "active"],
    audit_action: str,
    response_action: Literal["suspended", "resumed"],
) -> TenantActionResponse:
    current = await service.get_tenant_admin(slug)
    if current is None:
        raise AppError(status=404, code="tenant_not_found", title="Tenant not found")
    if current["status"] == target:
        return TenantActionResponse(tenant=_row(current), action=response_action)

    data = await service.set_tenant_status(
        slug=slug,
        target=target,
        action=audit_action,
        actor_user_id=user.id,
    )
    if data is None:
        raise AppError(
            status=409,
            code="invalid_tenant_state",
            title="Tenant cannot change state",
            detail=f"Tenant is {current['status']}.",
        )
    await tenancy.invalidate_tenant_cache(slug)
    return TenantActionResponse(tenant=_row(data), action=response_action)


@router.post(
    "/migrations/tenants",
    response_model=TenantMigrationSummary,
    summary="Apply pending tenant migrations",
)
async def migrate_tenants(user: Operator) -> TenantMigrationSummary:
    results = await tenancy.migrate_all_tenants()
    await service.record_audit(
        tenant_id=None,
        actor_user_id=user.id,
        action="tenant.migrations_run",
        resource_type="tenant_migrations",
        resource_id="all",
        metadata={
            "tenants": len(results),
            "applied": sum(len(applied) for _, applied in results),
        },
    )
    return TenantMigrationSummary(
        results=[TenantMigrationResult(slug=slug, applied=applied) for slug, applied in results]
    )


@router.get("/audit", response_model=AuditList, summary="Query the audit log")
async def audit_log(
    _: Operator,
    tenant: str | None = None,
    action: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
) -> AuditList:
    items, total = await service.query_audit(
        tenant_slug=tenant,
        action=action,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
    return AuditList(
        items=[AuditRow(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/audit/actions", response_model=list[str], summary="Known audit actions")
async def audit_actions(_: Operator) -> list[str]:
    return await service.audit_actions()


@router.get("/health", response_model=OpsHealth, summary="Operator health summary")
async def ops_health(request: Request, _: Operator) -> OpsHealth:
    settings = get_settings()
    checks = {
        "postgres": await check_postgres(request),
        "redis": await check_redis(request),
        "minio": await check_minio(request),
    }
    queue = await service.queue_depth()
    counts = await service.tenant_status_counts()
    started = getattr(request.app.state, "started_at", time.time())
    return OpsHealth(
        status="ok" if all(state == "ok" for state in checks.values()) else "degraded",
        version=settings.version,
        uptime_seconds=max(0, int(time.time() - started)),
        checks=checks,
        queue=QueueDepth(**queue),
        tenants=TenantCounts(**counts),
    )
