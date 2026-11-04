"""Request/response schemas for auth and the current user."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    tenant_slug: str = Field(min_length=2)
    email: EmailStr
    password: str
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    tenant_slug: str = Field(min_length=2)
    email: EmailStr
    password: str


class PlatformLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    all_sessions: bool = False


class VerifyEmailConfirm(BaseModel):
    token: str = Field(min_length=20)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=12, max_length=256)


class MessageResponse(BaseModel):
    message: str


class UserSummary(BaseModel):
    id: UUID
    email: str
    role: str | None


class TokenResponse(BaseModel):
    user: UserSummary
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - not a secret
    expires_in: int
    scope: str = "tenant"


class TenantSummary(BaseModel):
    id: UUID
    slug: str
    name: str


class MembershipOut(BaseModel):
    role: str
    tenant: TenantSummary


class ProfileOut(BaseModel):
    display_name: str
    timezone: str
    avatar_file_id: UUID | None


class MeResponse(BaseModel):
    id: UUID
    email: str
    is_verified: bool
    is_platform_admin: bool
    membership: MembershipOut | None
    profile: ProfileOut | None
