"""Tenant identity for the current request.

The context is a ``ContextVar`` so it never leaks between concurrent requests.
It is intentionally *not* the source of authorization: the JWT ``tid`` claim must
still match this context (M2).
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")


class InvalidSlug(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TenantContext:
    id: UUID
    slug: str
    name: str
    status: str
    schema: str


current_tenant: ContextVar[TenantContext | None] = ContextVar("current_tenant", default=None)


def schema_name(slug: str) -> str:
    """Map a slug to a schema identifier.

    Hyphens become underscores because an unquoted identifier cannot contain
    one. The slug format check keeps the result safe to interpolate (always
    quoted anyway).
    """
    if not SLUG_PATTERN.match(slug):
        raise InvalidSlug(f"invalid slug: {slug!r}")
    return "tenant_" + slug.replace("-", "_")


def get_tenant() -> TenantContext | None:
    return current_tenant.get()
