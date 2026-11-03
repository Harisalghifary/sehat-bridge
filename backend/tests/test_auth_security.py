from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from app.auth.security import (
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import get_settings


def test_password_roundtrip() -> None:
    hashed = hash_password("a-long-enough-password")
    assert hashed.startswith("$argon2")
    assert verify_password("a-long-enough-password", hashed) is True


def test_wrong_password_is_rejected() -> None:
    hashed = hash_password("a-long-enough-password")
    assert verify_password("another-password", hashed) is False


def test_unknown_hash_does_not_raise() -> None:
    assert verify_password("anything", "!unset") is False


def _claims(*, exp: datetime) -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "iss": get_settings().jwt_issuer,
        "aud": get_settings().jwt_audience,
        "sub": str(uuid4()),
        "tid": None,
        "role": None,
        "scope": "platform",
        "fid": None,
        "jti": str(uuid4()),
        "iat": now,
        "exp": exp,
    }


def test_expired_access_token_is_rejected() -> None:
    settings = get_settings()
    token = jwt.encode(
        _claims(exp=datetime.now(UTC) - timedelta(minutes=1)),
        settings.secret_key,
        algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_signed_with_another_key_is_rejected() -> None:
    token = jwt.encode(
        _claims(exp=datetime.now(UTC) + timedelta(minutes=5)),
        "a-different-key-that-is-long-enough-32",
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)
