"""Password hashing, JWT access tokens, and opaque refresh tokens."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.config import get_settings

_hasher = PasswordHash.recommended()
logger = logging.getLogger(__name__)

# Verified on failed logins so unknown emails cost the same time as known ones.
DUMMY_HASH = _hasher.hash("dummy-password-for-timing-only")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(password, hashed)
    except (UnknownHashError, ValueError):
        return False


def waste_verify_time() -> None:
    verify_password("definitely-not-the-password", DUMMY_HASH)


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def create_access_token(
    *,
    user_id: UUID,
    tenant_id: UUID | None,
    role: str | None,
    scope: str,
    family_id: UUID | None,
) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.access_token_ttl_seconds)
    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": str(user_id),
        "tid": str(tenant_id) if tenant_id else None,
        "role": role,
        "scope": scope,
        "fid": str(family_id) if family_id else None,
        "jti": str(uuid4()),
        "iat": now,
        "exp": expires,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, settings.access_token_ttl_seconds


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "iss", "aud", "sub", "jti"]},
    )


def remaining_lifetime(exp: int) -> int:
    return max(int(exp - datetime.now(UTC).timestamp()), 1)


async def blacklist_access_token(redis: Any, jti: str, exp: int) -> None:
    """Best effort: logout must not fail because Redis is down."""
    try:
        await redis.set(f"sb:jwt:block:{jti}", "1", ex=remaining_lifetime(exp))
    except Exception:  # pragma: no cover - availability path
        logger.warning("could not blacklist access token", exc_info=True)


async def is_access_token_blacklisted(redis: Any, jti: str) -> bool:
    """Fail closed: if revocation cannot be checked, do not accept the token."""
    try:
        return bool(await redis.exists(f"sb:jwt:block:{jti}"))
    except Exception as exc:  # pragma: no cover - availability path
        from app.errors import AppError

        raise AppError(
            status=503,
            code="auth_unavailable",
            title="Authentication temporarily unavailable",
            detail="The revocation store is unreachable.",
        ) from exc
