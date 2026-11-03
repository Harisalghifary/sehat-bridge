"""Integration API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CredentialsIn(BaseModel):
    client_id: str = Field(min_length=1, max_length=255)
    client_secret: str = Field(default="", max_length=500)
    organization_id: str = Field(min_length=1, max_length=100)


class CredentialsOut(BaseModel):
    provider: str
    status: str
    has_secret: bool
    client_id: str | None
    organization_id: str | None
    base_url: str
    last_verified_at: datetime | None
    last_error: str | None
    mode: str


class TestConnectionOut(BaseModel):
    status: Literal["connected", "error"]
    latency_ms: int | None = None
    error: str | None = None


class SyncRequest(BaseModel):
    kind: Literal["organization", "patient"]


class SyncQueued(BaseModel):
    job_id: UUID
    status: str


class JobOut(BaseModel):
    id: UUID
    kind: str
    status: str
    attempts: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    fhir_id: str | None = None


class JobDetail(JobOut):
    response_body: dict[str, Any] | None = None


class JobList(BaseModel):
    items: list[JobOut]
    next_cursor: str | None
    has_more: bool
