"""Fernet encryption for tenant integration secrets.

``APP_ENCRYPTION_KEY`` is an arbitrary passphrase in configuration, so the
32-byte Fernet key is derived with SHA-256. It is deliberately separate from
``SECRET_KEY`` so rotating JWT signing does not orphan stored secrets.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class SecretBox:
    def __init__(self, passphrase: str) -> None:
        key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest())
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> bytes:
        return self._fernet.encrypt(value.encode("utf-8"))

    def decrypt(self, value: bytes) -> str:
        return self._fernet.decrypt(value).decode("utf-8")


@lru_cache
def get_secret_box() -> SecretBox:
    return SecretBox(get_settings().app_encryption_key)


__all__ = ["InvalidToken", "SecretBox", "get_secret_box"]
