"""File metadata and upload schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PresignUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)


class PresignUpload(BaseModel):
    url: str
    fields: dict[str, str]
    method: Literal["POST"] = "POST"
    expires_in: int


class PresignUploadResponse(BaseModel):
    file_id: UUID
    upload: PresignUpload
    max_size_bytes: int


class FileOut(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    sha256: str | None
    owner_user_id: UUID
    created_at: datetime
    completed_at: datetime | None


class FileList(BaseModel):
    items: list[FileOut]
    next_cursor: str | None
    has_more: bool


class DownloadResponse(BaseModel):
    url: str
    expires_in: int


class FileUsage(BaseModel):
    files: int
    used_bytes: int
    quota_bytes: int
