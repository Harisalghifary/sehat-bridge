"""Authentication flows: register, login, refresh, logout, platform login."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit import write_audit as _audit
from app.auth.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
    waste_verify_time,
)
from app.config import get_settings
from app.db.session import public_session
from app.db.tenant_context import TenantContext, schema_name
from app.errors import AppError

MIN_PASSWORD_LENGTH = 12


@dataclass(slots=True)
class AuthResult:
    user_id: UUID
    email: str
    role: str | None
    scope: str
    access_token: str
    refresh_token: str
    expires_in: int
    tenant: TenantContext | None


async def _fetch_tenant(session: AsyncSession, slug: str) -> dict[str, Any] | None:
    row = (
        (
            await session.execute(
                text("SELECT id, slug, name, status FROM public.tenants WHERE slug = :slug"),
                {"slug": slug},
            )
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def _as_tenant(row: dict[str, Any]) -> TenantContext:
    return TenantContext(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        status=row["status"],
        schema=schema_name(row["slug"]),
    )


async def _scope_session(session: AsyncSession, tenant: TenantContext) -> None:
    await session.execute(
        text("SELECT set_config('search_path', :path, true)"),
        {"path": f"{tenant.schema}, public"},
    )
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant.id)},
    )


async def _issue(
    session: AsyncSession,
    *,
    user_id: UUID,
    email: str,
    tenant: TenantContext | None,
    role: str | None,
    scope: str,
    family_id: UUID | None = None,
) -> AuthResult:
    settings = get_settings()
    family = family_id or uuid4()
    refresh = new_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)

    await session.execute(
        text(
            """
            INSERT INTO public.refresh_tokens
                (user_id, tenant_id, token_hash, family_id, expires_at)
            VALUES (:user_id, :tenant_id, :token_hash, :family_id, :expires_at)
            """
        ),
        {
            "user_id": user_id,
            "tenant_id": tenant.id if tenant else None,
            "token_hash": hash_refresh_token(refresh),
            "family_id": family,
            "expires_at": expires_at,
        },
    )

    access, expires_in = create_access_token(
        user_id=user_id,
        tenant_id=tenant.id if tenant else None,
        role=role,
        scope=scope,
        family_id=family,
    )
    return AuthResult(
        user_id=user_id,
        email=email,
        role=role,
        scope=scope,
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        tenant=tenant,
    )


async def register(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    tenant_slug: str,
    email: str,
    password: str,
    display_name: str | None,
    ip: str | None,
) -> AuthResult:
    settings = get_settings()
    if not settings.registration_enabled:
        raise AppError(
            status=403,
            code="registration_disabled",
            title="Registration is disabled",
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AppError(
            status=422,
            code="weak_password",
            title="Password is too short",
            detail=f"Use at least {MIN_PASSWORD_LENGTH} characters.",
        )

    async with public_session(sessionmaker) as session:
        tenant_row = await _fetch_tenant(session, tenant_slug)
        if tenant_row is None or tenant_row["status"] != "active":
            raise AppError(
                status=404,
                code="tenant_not_found",
                title="Tenant not found",
            )
        tenant = _as_tenant(tenant_row)
        await _scope_session(session, tenant)

        existing = (
            await session.execute(
                text("SELECT 1 FROM public.users WHERE email = :email"),
                {"email": email},
            )
        ).scalar()
        if existing:
            raise AppError(status=409, code="email_in_use", title="Email already registered")

        try:
            user_id: UUID = (
                await session.execute(
                    text(
                        """
                        INSERT INTO public.users (email, hashed_password)
                        VALUES (:email, :password_hash)
                        RETURNING id
                        """
                    ),
                    {"email": email, "password_hash": hash_password(password)},
                )
            ).scalar_one()
        except IntegrityError as exc:
            raise AppError(
                status=409, code="email_in_use", title="Email already registered"
            ) from exc

        await session.execute(
            text(
                """
                INSERT INTO public.memberships (user_id, tenant_id, role)
                VALUES (:user_id, :tenant_id, 'member')
                """
            ),
            {"user_id": user_id, "tenant_id": tenant.id},
        )
        await session.execute(
            text(
                """
                INSERT INTO profiles (user_id, display_name)
                VALUES (:user_id, :display_name)
                ON CONFLICT (user_id) DO NOTHING
                """
            ),
            {
                "user_id": user_id,
                "display_name": display_name or email.split("@", 1)[0],
            },
        )
        result = await _issue(
            session,
            user_id=user_id,
            email=email,
            tenant=tenant,
            role="member",
            scope="tenant",
        )
        await _audit(session, "auth.register", tenant_id=tenant.id, actor_user_id=user_id, ip=ip)
        return result


async def login(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    tenant_slug: str,
    email: str,
    password: str,
    ip: str | None,
) -> AuthResult:
    error: AppError | None = None
    async with public_session(sessionmaker) as session:
        tenant_row = await _fetch_tenant(session, tenant_slug)
        tenant = _as_tenant(tenant_row) if tenant_row else None
        if tenant is None or tenant.status != "active":
            waste_verify_time()
            await _audit(
                session,
                "auth.login_failed",
                tenant_id=tenant.id if tenant else None,
                ip=ip,
                metadata={"reason": "tenant"},
            )
            error = AppError(
                status=401,
                code="invalid_credentials",
                title="Invalid credentials",
            )
        else:
            row = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT u.id, u.email, u.hashed_password, u.is_active,
                               u.is_verified, u.is_platform_admin, m.role
                          FROM public.users u
                          JOIN public.memberships m
                            ON m.user_id = u.id AND m.tenant_id = :tenant_id
                         WHERE u.email = :email
                        """
                        ),
                        {"email": email, "tenant_id": tenant.id},
                    )
                )
                .mappings()
                .first()
            )

            if (
                row is None
                or not row["is_active"]
                or not verify_password(password, row["hashed_password"])
            ):
                if row is None or not row["is_active"]:
                    waste_verify_time()
                await _audit(
                    session,
                    "auth.login_failed",
                    tenant_id=tenant.id,
                    ip=ip,
                    metadata={"reason": "credentials"},
                )
                error = AppError(
                    status=401,
                    code="invalid_credentials",
                    title="Invalid credentials",
                )
            else:
                result = await _issue(
                    session,
                    user_id=row["id"],
                    email=row["email"],
                    tenant=tenant,
                    role=row["role"],
                    scope="tenant",
                )
                await _audit(
                    session,
                    "auth.login",
                    tenant_id=tenant.id,
                    actor_user_id=row["id"],
                    ip=ip,
                )
                return result

    assert error is not None
    raise error


async def refresh(
    sessionmaker: async_sessionmaker[AsyncSession], *, token: str, ip: str | None
) -> AuthResult:
    digest = hash_refresh_token(token)
    reused = False
    async with public_session(sessionmaker) as session:
        row = (
            (
                await session.execute(
                    text(
                        """
                    SELECT rt.id, rt.user_id, rt.tenant_id, rt.family_id,
                           rt.expires_at, rt.revoked_at,
                           u.email, u.is_active, u.is_platform_admin,
                           m.role
                      FROM public.refresh_tokens rt
                      JOIN public.users u ON u.id = rt.user_id
                      LEFT JOIN public.memberships m
                        ON m.user_id = rt.user_id AND m.tenant_id = rt.tenant_id
                     WHERE rt.token_hash = :digest
                     FOR UPDATE OF rt
                    """
                    ),
                    {"digest": digest},
                )
            )
            .mappings()
            .first()
        )

        if row is None:
            raise AppError(status=401, code="invalid_refresh", title="Invalid refresh token")

        if row["revoked_at"] is not None:
            # Reuse: kill the whole chain, commit, then fail.
            await session.execute(
                text(
                    """
                    UPDATE public.refresh_tokens
                       SET revoked_at = now()
                     WHERE family_id = :family_id AND revoked_at IS NULL
                    """
                ),
                {"family_id": row["family_id"]},
            )
            await _audit(
                session,
                "auth.refresh_reuse",
                tenant_id=row["tenant_id"],
                actor_user_id=row["user_id"],
                ip=ip,
            )
            reused = True
        elif row["expires_at"] <= datetime.now(UTC) or not row["is_active"]:
            raise AppError(status=401, code="invalid_refresh", title="Invalid refresh token")
        elif row["tenant_id"] is None and not row["is_platform_admin"]:
            raise AppError(status=401, code="invalid_refresh", title="Invalid refresh token")
        else:
            tenant: TenantContext | None = None
            role: str | None = None
            scope = "platform"
            if row["tenant_id"] is not None:
                tenant_row = (
                    (
                        await session.execute(
                            text(
                                "SELECT id, slug, name, status FROM public.tenants WHERE id = :id"
                            ),
                            {"id": row["tenant_id"]},
                        )
                    )
                    .mappings()
                    .first()
                )
                if tenant_row is None or tenant_row["status"] != "active":
                    raise AppError(
                        status=403,
                        code="tenant_inactive",
                        title="Tenant is not active",
                    )
                tenant = _as_tenant(dict(tenant_row))
                role = row["role"]
                scope = "tenant"

            settings = get_settings()
            family = row["family_id"]
            new_token = new_refresh_token()
            new_id = uuid4()
            expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
            await session.execute(
                text(
                    """
                    INSERT INTO public.refresh_tokens
                        (id, user_id, tenant_id, token_hash, family_id, expires_at)
                    VALUES (
                        :id, :user_id, :tenant_id, :token_hash, :family_id,
                        :expires_at
                    )
                    """
                ),
                {
                    "id": new_id,
                    "user_id": row["user_id"],
                    "tenant_id": row["tenant_id"],
                    "token_hash": hash_refresh_token(new_token),
                    "family_id": family,
                    "expires_at": expires_at,
                },
            )
            await session.execute(
                text(
                    """
                    UPDATE public.refresh_tokens
                       SET revoked_at = now(), replaced_by = :new_id
                     WHERE id = :old_id
                    """
                ),
                {"new_id": new_id, "old_id": row["id"]},
            )

            access, expires_in = create_access_token(
                user_id=row["user_id"],
                tenant_id=row["tenant_id"],
                role=role,
                scope=scope,
                family_id=family,
            )
            await _audit(
                session,
                "auth.refresh",
                tenant_id=row["tenant_id"],
                actor_user_id=row["user_id"],
                ip=ip,
            )
            return AuthResult(
                user_id=row["user_id"],
                email=row["email"],
                role=role,
                scope=scope,
                access_token=access,
                refresh_token=new_token,
                expires_in=expires_in,
                tenant=tenant,
            )

    if reused:
        raise AppError(status=401, code="invalid_refresh", title="Invalid refresh token")
    raise AppError(status=401, code="invalid_refresh", title="Invalid refresh token")


async def platform_login(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    email: str,
    password: str,
    ip: str | None,
) -> AuthResult:
    error: AppError | None = None
    async with public_session(sessionmaker) as session:
        row = (
            (
                await session.execute(
                    text(
                        """
                    SELECT id, email, hashed_password, is_active, is_platform_admin
                      FROM public.users
                     WHERE email = :email AND is_platform_admin = true
                    """
                    ),
                    {"email": email},
                )
            )
            .mappings()
            .first()
        )

        if (
            row is None
            or not row["is_active"]
            or not verify_password(password, row["hashed_password"])
        ):
            waste_verify_time()
            await _audit(
                session,
                "auth.platform_login_failed",
                ip=ip,
                metadata={"email": email},
            )
            error = AppError(
                status=401,
                code="invalid_credentials",
                title="Invalid credentials",
            )
        else:
            result = await _issue(
                session,
                user_id=row["id"],
                email=row["email"],
                tenant=None,
                role=None,
                scope="platform",
            )
            await _audit(
                session,
                "auth.platform_login",
                actor_user_id=row["id"],
                ip=ip,
            )
            return result

    assert error is not None
    raise error


async def logout(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    user_id: UUID,
    family_id: UUID | None,
    all_sessions: bool,
    ip: str | None,
) -> None:
    async with public_session(sessionmaker) as session:
        if all_sessions and family_id is not None:
            await session.execute(
                text(
                    """
                    UPDATE public.refresh_tokens
                       SET revoked_at = now()
                     WHERE family_id = :family_id
                       AND user_id = :user_id
                       AND revoked_at IS NULL
                    """
                ),
                {"family_id": family_id, "user_id": user_id},
            )
        await _audit(
            session,
            "auth.logout",
            actor_user_id=user_id,
            ip=ip,
            metadata={"all_sessions": all_sessions},
        )


async def get_tenant_by_id(engine: Any, tenant_id: UUID) -> TenantContext | None:
    async with engine.connect() as conn:
        row = (
            (
                await conn.execute(
                    text("SELECT id, slug, name, status FROM public.tenants WHERE id = :id"),
                    {"id": tenant_id},
                )
            )
            .mappings()
            .first()
        )
    return _as_tenant(dict(row)) if row else None
