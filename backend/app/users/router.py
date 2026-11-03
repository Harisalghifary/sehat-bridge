"""Current-user endpoints. Roles and member management arrive in M3."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from app.auth.dependencies import AuthUser, get_current_user
from app.auth.schemas import (
    MembershipOut,
    MeResponse,
    ProfileOut,
    TenantSummary,
)
from app.db.session import tenant_session

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=MeResponse, summary="Current user and membership")
async def me(request: Request, user: AuthUser = Depends(get_current_user)) -> MeResponse:
    if user.tenant is None:
        return MeResponse(
            id=user.id,
            email=user.email,
            is_verified=user.is_verified,
            is_platform_admin=user.is_platform_admin,
            membership=None,
            profile=None,
        )

    async with tenant_session(request.app.state.sessionmaker, user.tenant) as session:
        row: Any = (
            (
                await session.execute(
                    text(
                        """
                    SELECT display_name, timezone, avatar_file_id
                      FROM profiles WHERE user_id = :user_id
                    """
                    ),
                    {"user_id": user.id},
                )
            )
            .mappings()
            .first()
        )

    profile = (
        ProfileOut(
            display_name=row["display_name"],
            timezone=row["timezone"],
            avatar_file_id=row["avatar_file_id"],
        )
        if row
        else None
    )
    return MeResponse(
        id=user.id,
        email=user.email,
        is_verified=user.is_verified,
        is_platform_admin=user.is_platform_admin,
        membership=MembershipOut(
            role=user.role or "member",
            tenant=TenantSummary(id=user.tenant.id, slug=user.tenant.slug, name=user.tenant.name),
        ),
        profile=profile,
    )
