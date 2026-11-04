"""Schemas for the platform operator console."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class TenantRow(BaseModel):
    slug: str
    name: str
    status: str
    plan: str
    members: int
    owner_email: str | None
    failure_note: str | None
    created_at: datetime
    updated_at: datetime


class TenantDetail(TenantRow):
    queued_jobs: int
    failed_jobs: int


class TenantList(BaseModel):
    items: list[TenantRow]


class ProvisionRequest(BaseModel):
    slug: str = Field(
        min_length=2,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9_-]{1,62}$",
    )
    name: str = Field(min_length=2, max_length=120)
    owner_email: EmailStr
    owner_display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=12, max_length=256)


class ProvisionStep(BaseModel):
    key: str
    label: str
    status: Literal["done", "failed"]


class ProvisionResponse(BaseModel):
    tenant: TenantDetail
    owner_email: str
    steps: list[ProvisionStep]


class TenantActionResponse(BaseModel):
    tenant: TenantRow
    action: Literal["suspended", "resumed"]


class AuditRow(BaseModel):
    id: int
    tenant_slug: str | None
    tenant_name: str | None
    actor_email: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    metadata: dict[str, Any]
    created_at: datetime


class AuditList(BaseModel):
    items: list[AuditRow]
    total: int
    limit: int
    offset: int


class TenantMigrationResult(BaseModel):
    slug: str
    applied: list[str]


class TenantMigrationSummary(BaseModel):
    results: list[TenantMigrationResult]


class QueueDepth(BaseModel):
    queued: int
    running: int
    failed: int
    dead: int


class TenantCounts(BaseModel):
    active: int
    suspended: int
    provisioning: int
    failed: int


class OpsHealth(BaseModel):
    status: str
    version: str
    uptime_seconds: int
    checks: dict[str, Literal["ok", "error"]]
    queue: QueueDepth
    tenants: TenantCounts
