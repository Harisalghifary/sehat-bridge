"""Public lead capture schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LeadIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    facility_name: str = Field(min_length=2, max_length=200)
    facility_type: Literal["klinik", "rumah_sakit", "lab", "apotek", "lainnya"] | None = None
    city: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    message: str | None = Field(default=None, max_length=2000)
    website: str = Field(default="", max_length=200)
    elapsed_ms: int = Field(default=0, ge=0)


class LeadAccepted(BaseModel):
    message: str
