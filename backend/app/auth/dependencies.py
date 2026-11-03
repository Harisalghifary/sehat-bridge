"""Authentication dependencies: bearer token -> user + tenant + role."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.auth.security import decode_access_token, is_access_token_blacklisted
from app.auth.service import get_tenant_by_id
from app.db.session import public_session, tenant_session
from app.db.tenant_context import TenantContext, current_tenant
from app.errors import AppError

bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthUser:
    id: UUID
    email: str
    role: str | None
    scope: str
    tenant: TenantContext | None
    jti: str
    family_id: UUID | None
    exp: int
    is_verified: bool
    is_platform_admin: bool


def _unauthorized(code: str = "invalid_token", detail: str | None = None) -> AppError:
    return AppError(
        status=401,
        code=code,
        title="Not authenticated",
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthUser:
    if credentials is None:
        raise _unauthorized("missing_token", "Authorization header is required.")

    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _unauthorized("invalid_token", "The access token is invalid.") from exc

    jti = str(claims["jti"])
    if await is_access_token_blacklisted(request.app.state.redis, jti):
        raise _unauthorized("token_revoked", "The access token was revoked.")

    user_id = UUID(claims["sub"])
    scope = str(claims.get("scope") or "tenant")
    family_id = UUID(claims["fid"]) if claims.get("fid") else None
    exp = int(claims["exp"])

    if scope == "platform":
        async with public_session(request.app.state.sessionmaker) as session:
            row = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT email, is_active, is_verified, is_platform_admin
                          FROM public.users WHERE id = :id
                        """
                        ),
                        {"id": user_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None or not row["is_active"] or not row["is_platform_admin"]:
            raise _unauthorized("invalid_token")
        return AuthUser(
            id=user_id,
            email=row["email"],
            role=None,
            scope="platform",
            tenant=None,
            jti=jti,
            family_id=family_id,
            exp=exp,
            is_verified=row["is_verified"],
            is_platform_admin=True,
        )

    tenant_id_raw = claims.get("tid")
    if not tenant_id_raw:
        raise _unauthorized("invalid_token", "The access token has no tenant.")

    tenant_id = UUID(tenant_id_raw)
    async with public_session(request.app.state.sessionmaker) as session:
        row = (
            (
                await session.execute(
                    text(
                        """
                    SELECT u.email, u.is_active, u.is_verified, u.is_platform_admin,
                           m.role
                      FROM public.users u
                      JOIN public.memberships m
                        ON m.user_id = u.id AND m.tenant_id = :tenant_id
                     WHERE u.id = :user_id
                    """
                    ),
                    {"user_id": user_id, "tenant_id": tenant_id},
                )
            )
            .mappings()
            .first()
        )

    if row is None or not row["is_active"]:
        raise _unauthorized("invalid_token")

    tenant = await get_tenant_by_id(request.app.state.engine, tenant_id)
    if tenant is None or tenant.status != "active":
        raise AppError(status=403, code="tenant_inactive", title="Tenant is not active")

    hint: TenantContext | None = getattr(request.state, "tenant", None)
    if hint is not None and hint.id != tenant.id:
        raise AppError(
            status=403,
            code="tenant_mismatch",
            title="Tenant mismatch",
            detail="Token tenant does not match X-Tenant-ID.",
        )

    request.state.tenant = tenant
    current_tenant.set(tenant)

    return AuthUser(
        id=user_id,
        email=row["email"],
        role=row["role"],
        scope="tenant",
        tenant=tenant,
        jti=jti,
        family_id=family_id,
        exp=exp,
        is_verified=row["is_verified"],
        is_platform_admin=row["is_platform_admin"],
    )


def require_role(*roles: str) -> Callable[..., Any]:
    async def dependency(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.scope != "tenant" or user.role not in roles:
            raise AppError(
                status=403,
                code="insufficient_role",
                title="Insufficient role",
                detail=f"Requires one of: {', '.join(roles)}.",
            )
        return user

    return dependency


async def tenant_db(
    request: Request, user: AuthUser = Depends(get_current_user)
) -> AsyncIterator[object]:
    if user.tenant is None:
        raise AppError(status=403, code="tenant_required", title="A tenant is required")
    async with tenant_session(request.app.state.sessionmaker, user.tenant) as session:
        yield session
