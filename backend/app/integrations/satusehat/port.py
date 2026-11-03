"""SATUSEHAT port: the only interface domain code is allowed to use."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Credentials:
    client_id: str
    client_secret: str
    base_url: str


@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class OrganizationDraft:
    local_id: UUID
    name: str
    identifier: str


@dataclass(frozen=True, slots=True)
class PatientDraft:
    local_id: UUID
    identifier: str
    display_name: str


@dataclass(frozen=True, slots=True)
class FhirRef:
    id: str
    resource_type: str


class SatusehatError(Exception):
    """Normalised adapter failure.

    ``retryable`` decides whether the outbox backs off or fails immediately.
    Terminal errors are 4xx validation problems; transport errors, timeouts,
    5xx and 429 are retryable.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.body = body


@runtime_checkable
class SatusehatPort(Protocol):
    async def issue_token(self, creds: Credentials) -> AccessToken: ...

    async def put_organization(self, token: AccessToken, org: OrganizationDraft) -> FhirRef: ...

    async def put_patient(self, token: AccessToken, patient: PatientDraft) -> FhirRef: ...

    async def get_resource(
        self, token: AccessToken, resource_type: str, rid: str
    ) -> dict[str, Any]: ...


def join_url(base_url: str, path: str) -> str:
    """Append a FHIR path while preserving an injected ``?fail=`` query."""
    parts = urlsplit(base_url)
    base_path = parts.path.rstrip("/")
    return urlunsplit(
        (parts.scheme, parts.netloc, f"{base_path}/{path.lstrip('/')}", parts.query, "")
    )


def origin_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def retryable_status(status: int) -> bool:
    return status >= 500 or status in {408, 429}
