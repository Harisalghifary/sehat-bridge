"""Current user, member list, and role management."""

from __future__ import annotations

from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.auth.dependencies import AuthUser, get_current_user, require_role, tenant_db
from app.auth.rate_limit import client_ip
from app.auth.schemas import (
    MembershipOut,
    MeResponse,
    ProfileOut,
    TenantSummary,
)
from app.db.session import tenant_session
from app.errors import AppError
from app.pagination import decode_cursor, encode_cursor
from app.users.schemas import MemberList, MemberOut, ProfileUpdate, RoleUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])

PROFILE_COLUMNS = "user_id, display_name, timezone, avatar_file_id"


def _profile_out(row: Any) -> ProfileOut:
    return ProfileOut(
        display_name=row["display_name"],
        timezone=row["timezone"],
        avatar_file_id=row["avatar_file_id"],
    )


async def _fetch_profile(session: AsyncSession, user_id: UUID) -> Any:
    return (
        (
            await session.execute(
                text(f"SELECT {PROFILE_COLUMNS} FROM profiles WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
        )
        .mappings()
        .first()
    )


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
        row = await _fetch_profile(session, user.id)

    return MeResponse(
        id=user.id,
        email=user.email,
        is_verified=user.is_verified,
        is_platform_admin=user.is_platform_admin,
        membership=MembershipOut(
            role=user.role or "member",
            tenant=TenantSummary(id=user.tenant.id, slug=user.tenant.slug, name=user.tenant.name),
        ),
        profile=_profile_out(row) if row else None,
    )


@router.patch("/me", response_model=ProfileOut, summary="Update your profile")
async def update_me(
    body: ProfileUpdate,
    request: Request,
    user: AuthUser = Depends(get_current_user),
) -> ProfileOut:
    if user.tenant is None:
        raise AppError(status=403, code="tenant_required", title="A tenant is required")

    fields = body.model_fields_set
    sets: list[str] = []
    params: dict[str, Any] = {"user_id": user.id}

    if "display_name" in fields:
        if not isinstance(body.display_name, str) or not body.display_name.strip():
            raise AppError(
                status=422,
                code="invalid_display_name",
                title="Display name is required",
            )
        sets.append("display_name = :display_name")
        params["display_name"] = body.display_name.strip()

    if "timezone" in fields:
        if not isinstance(body.timezone, str):
            raise AppError(status=422, code="invalid_timezone", title="Invalid timezone")
        try:
            ZoneInfo(body.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise AppError(status=422, code="invalid_timezone", title="Invalid timezone") from exc
        sets.append("timezone = :timezone")
        params["timezone"] = body.timezone

    if "avatar_file_id" in fields:
        sets.append("avatar_file_id = :avatar_file_id")
        params["avatar_file_id"] = body.avatar_file_id

    async with tenant_session(request.app.state.sessionmaker, user.tenant) as session:
        if sets:
            await session.execute(
                text(
                    f"UPDATE profiles SET {', '.join(sets)}, updated_at = now() "
                    "WHERE user_id = :user_id"
                ),
                params,
            )
        row = await _fetch_profile(session, user.id)

    if row is None:
        raise AppError(status=404, code="profile_not_found", title="Profile not found")
    return _profile_out(row)


@router.get("", response_model=MemberList, summary="List members of the current tenant")
async def list_members(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    user: AuthUser = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(tenant_db),
) -> MemberList:
    tenant = user.tenant
    if tenant is None:
        raise AppError(status=403, code="tenant_required", title="A tenant is required")
    params: dict[str, Any] = {"tenant_id": tenant.id, "limit": limit + 1}
    condition = ""
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)
        condition = "AND (m.created_at, m.user_id) < (:cursor_ts, :cursor_id)"
        params["cursor_ts"] = cursor_ts
        params["cursor_id"] = cursor_id

    query = f"""
        SELECT u.id, u.email, u.is_verified, m.role, m.created_at,
               p.display_name
          FROM public.memberships m
          JOIN public.users u ON u.id = m.user_id
          LEFT JOIN profiles p ON p.user_id = u.id
         WHERE m.tenant_id = :tenant_id {condition}
         ORDER BY m.created_at DESC, m.user_id DESC
         LIMIT :limit
    """
    rows = (await session.execute(text(query), params)).mappings().all()

    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(last["created_at"], last["id"])

    return MemberList(
        items=[
            MemberOut(
                id=row["id"],
                email=row["email"],
                role=row["role"],
                display_name=row["display_name"],
                is_verified=row["is_verified"],
                joined_at=row["created_at"],
            )
            for row in page
        ],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.patch(
    "/{user_id}/role",
    response_model=MemberOut,
    summary="Change a member's role",
)
async def update_role(
    user_id: UUID,
    body: RoleUpdate,
    request: Request,
    actor: AuthUser = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(tenant_db),
) -> MemberOut:
    tenant = actor.tenant
    if tenant is None:
        raise AppError(status=403, code="tenant_required", title="A tenant is required")

    target = (
        (
            await session.execute(
                text(
                    """
                SELECT u.id, u.email, u.is_verified, m.role, m.created_at,
                       p.display_name
                  FROM public.memberships m
                  JOIN public.users u ON u.id = m.user_id
                  LEFT JOIN profiles p ON p.user_id = u.id
                 WHERE m.tenant_id = :tenant_id AND m.user_id = :user_id
                 FOR UPDATE OF m
                """
                ),
                {"tenant_id": tenant.id, "user_id": user_id},
            )
        )
        .mappings()
        .first()
    )

    if target is None:
        raise AppError(status=404, code="user_not_found", title="User not found")

    old_role = target["role"]
    new_role = body.role

    if old_role == "owner" and actor.role != "owner":
        raise AppError(
            status=403,
            code="insufficient_role",
            title="Only an owner can change an owner",
        )
    if new_role == "owner" and actor.role != "owner":
        raise AppError(
            status=403,
            code="insufficient_role",
            title="Only an owner can grant owner",
        )

    if old_role == "owner" and new_role != "owner":
        owners = (
            (
                await session.execute(
                    text(
                        """
                    SELECT user_id FROM public.memberships
                     WHERE tenant_id = :tenant_id AND role = 'owner'
                     FOR UPDATE
                    """
                    ),
                    {"tenant_id": tenant.id},
                )
            )
            .scalars()
            .all()
        )
        if len(owners) <= 1:
            raise AppError(
                status=409,
                code="last_owner",
                title="The last owner cannot be demoted",
            )

    if old_role != new_role:
        await session.execute(
            text(
                """
                UPDATE public.memberships SET role = :role
                 WHERE tenant_id = :tenant_id AND user_id = :user_id
                """
            ),
            {"role": new_role, "tenant_id": tenant.id, "user_id": user_id},
        )
        await write_audit(
            session,
            "user.role_changed",
            tenant_id=tenant.id,
            actor_user_id=actor.id,
            ip=client_ip(request),
            metadata={
                "user_id": str(user_id),
                "from": old_role,
                "to": new_role,
            },
        )

    return MemberOut(
        id=target["id"],
        email=target["email"],
        role=new_role,
        display_name=target["display_name"],
        is_verified=target["is_verified"],
        joined_at=target["created_at"],
    )
