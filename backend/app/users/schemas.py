"""User and role schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    timezone: str | None = None
    avatar_file_id: UUID | None = None


class RoleUpdate(BaseModel):
    role: Literal["owner", "admin", "member"]


class MemberOut(BaseModel):
    id: UUID
    email: str
    role: str
    display_name: str | None
    is_verified: bool
    joined_at: datetime


class MemberList(BaseModel):
    items: list[MemberOut]
    next_cursor: str | None
    has_more: bool
