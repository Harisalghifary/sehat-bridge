"""Single-use email verification and password reset tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit import write_audit
from app.auth.security import hash_password
from app.config import get_settings
from app.db.session import public_session
from app.errors import AppError
from app.mailer import (
    password_reset_email,
    send_email,
    verification_email,
)

MIN_PASSWORD_LENGTH = 12


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


async def _issue_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    purpose: str,
    ttl_seconds: int,
) -> str:
    token = secrets.token_urlsafe(32)
    await session.execute(
        text(
            """
            INSERT INTO auth_tokens (user_id, purpose, token_hash, expires_at)
            VALUES (:user_id, :purpose, :hash, :expires_at)
            """
        ),
        {
            "user_id": user_id,
            "purpose": purpose,
            "hash": _hash(token),
            "expires_at": datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        },
    )
    return token


async def send_verification(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    user_id: UUID,
    email: str,
) -> None:
    settings = get_settings()
    async with public_session(sessionmaker) as session:
        token = await _issue_token(
            session,
            user_id=user_id,
            purpose="verify_email",
            ttl_seconds=settings.email_token_ttl_seconds,
        )
        await write_audit(
            session,
            "auth.verification_sent",
            actor_user_id=user_id,
            metadata={"email": email},
        )
    subject, body = verification_email(f"{settings.site_url.rstrip('/')}/verifikasi?token={token}")
    await send_email(to=email, subject=subject, text=body)


async def confirm_verification(
    sessionmaker: async_sessionmaker[AsyncSession], *, token: str
) -> str:
    async with public_session(sessionmaker) as session:
        row = (
            (
                await session.execute(
                    text(
                        """
                        SELECT id, user_id, expires_at, used_at
                          FROM auth_tokens
                         WHERE token_hash = :hash AND purpose = 'verify_email'
                         FOR UPDATE
                        """
                    ),
                    {"hash": _hash(token)},
                )
            )
            .mappings()
            .first()
        )
        if row is None or row["used_at"] is not None:
            raise AppError(
                status=400,
                code="invalid_verification_token",
                title="Verification link is invalid or already used",
            )
        if row["expires_at"] <= datetime.now(UTC):
            raise AppError(
                status=400,
                code="expired_verification_token",
                title="Verification link has expired",
            )
        await session.execute(
            text("UPDATE auth_tokens SET used_at = now() WHERE id = :id"),
            {"id": row["id"]},
        )
        await session.execute(
            text("UPDATE users SET is_verified = true, updated_at = now() WHERE id = :id"),
            {"id": row["user_id"]},
        )
        await write_audit(
            session,
            "auth.email_verified",
            actor_user_id=row["user_id"],
        )
    return "Email verified."


async def request_password_reset(
    sessionmaker: async_sessionmaker[AsyncSession], *, email: str
) -> None:
    """Always succeeds from the caller's point of view; only existing users get mail."""
    settings = get_settings()
    async with public_session(sessionmaker) as session:
        row = (
            (
                await session.execute(
                    text(
                        """
                        SELECT id, email FROM users
                         WHERE email = :email AND is_active = true
                        """
                    ),
                    {"email": email},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            # Constant-ish work so request timing does not enumerate accounts.
            await session.execute(text("SELECT pg_sleep(0.02)"))
            return
        token = await _issue_token(
            session,
            user_id=row["id"],
            purpose="reset_password",
            ttl_seconds=settings.password_reset_ttl_seconds,
        )
        await write_audit(
            session,
            "auth.password_reset_requested",
            actor_user_id=row["id"],
            metadata={"email": row["email"]},
        )
    subject, body = password_reset_email(
        f"{settings.site_url.rstrip('/')}/reset-sandi?token={token}"
    )
    await send_email(to=row["email"], subject=subject, text=body)


async def confirm_password_reset(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    token: str,
    new_password: str,
) -> None:
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise AppError(
            status=422,
            code="weak_password",
            title="Password is too short",
            detail=f"Use at least {MIN_PASSWORD_LENGTH} characters.",
        )
    async with public_session(sessionmaker) as session:
        row = (
            (
                await session.execute(
                    text(
                        """
                        SELECT id, user_id, expires_at, used_at
                          FROM auth_tokens
                         WHERE token_hash = :hash AND purpose = 'reset_password'
                         FOR UPDATE
                        """
                    ),
                    {"hash": _hash(token)},
                )
            )
            .mappings()
            .first()
        )
        if row is None or row["used_at"] is not None:
            raise AppError(
                status=400,
                code="invalid_reset_token",
                title="Reset link is invalid or already used",
            )
        if row["expires_at"] <= datetime.now(UTC):
            raise AppError(
                status=400,
                code="expired_reset_token",
                title="Reset link has expired",
            )
        await session.execute(
            text("UPDATE auth_tokens SET used_at = now() WHERE id = :id"),
            {"id": row["id"]},
        )
        await session.execute(
            text("UPDATE users SET hashed_password = :hash, updated_at = now() WHERE id = :id"),
            {"hash": hash_password(new_password), "id": row["user_id"]},
        )
        await session.execute(
            text(
                "UPDATE refresh_tokens SET revoked_at = now() "
                "WHERE user_id = :id AND revoked_at IS NULL"
            ),
            {"id": row["user_id"]},
        )
        await write_audit(
            session,
            "auth.password_reset",
            actor_user_id=row["user_id"],
        )
