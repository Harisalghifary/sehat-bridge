"""Live SATUSEHAT adapter (OAuth2 client-credentials + FHIR R4).

Selected only by ``SATUSEHAT_MODE=live``. It is exercised by an opt-in smoke
test when real credentials are present; the default pipeline never calls it.
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx
from redis.asyncio import Redis

from app.integrations.satusehat.port import (
    AccessToken,
    Credentials,
    FhirRef,
    OrganizationDraft,
    PatientDraft,
    SatusehatError,
    join_url,
    origin_url,
    retryable_status,
)

TOKEN_PREFIX = "sb:satusehat:token:"  # noqa: S105 - cache key prefix, not a secret


def _cache_key(creds: Credentials) -> str:
    digest = hashlib.sha256(f"{creds.client_id}|{creds.base_url}".encode()).hexdigest()
    return f"{TOKEN_PREFIX}{digest}"


class LiveAdapter:
    def __init__(
        self,
        base_url: str,
        *,
        redis: Redis | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url
        self.redis = redis
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        url: str,
        *,
        token: str | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/fhir+json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=headers, json=json, data=data)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise SatusehatError(f"Transport failure: {exc}", retryable=True) from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = {"raw": response.text[:500]}
            raise SatusehatError(
                f"SATUSEHAT returned HTTP {response.status_code}",
                status_code=response.status_code,
                retryable=retryable_status(response.status_code),
                body=body,
            )

        try:
            return dict(response.json())
        except ValueError as exc:
            raise SatusehatError("SATUSEHAT returned a non-JSON response", retryable=True) from exc

    async def issue_token(self, creds: Credentials) -> AccessToken:
        key = _cache_key(creds)
        if self.redis is not None:
            cached = await self.redis.get(key)
            if cached:
                return AccessToken(value=str(cached), expires_in=0)

        payload = await self._request(
            "POST",
            f"{origin_url(creds.base_url)}/oauth2/v1/accesstoken",
            data={
                "grant_type": "client_credentials",
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
            },
        )
        token = str(payload["access_token"])
        expires_in = int(payload.get("expires_in", 3600))
        if self.redis is not None:
            await self.redis.setex(key, max(expires_in - 60, 30), token)
        return AccessToken(value=token, expires_in=expires_in)

    async def put_organization(self, token: AccessToken, org: OrganizationDraft) -> FhirRef:
        payload = await self._request(
            "PUT",
            join_url(self.base_url, f"Organization/{org.identifier}"),
            token=token.value,
            json={
                "resourceType": "Organization",
                "id": org.identifier,
                "identifier": [{"system": "satusehat", "value": org.identifier}],
                "name": org.name,
                "active": True,
            },
        )
        rid = str(payload.get("id") or org.identifier)
        return FhirRef(id=rid, resource_type="Organization")

    async def put_patient(self, token: AccessToken, patient: PatientDraft) -> FhirRef:
        payload = await self._request(
            "PUT",
            join_url(self.base_url, f"Patient/{patient.identifier}"),
            token=token.value,
            json={
                "resourceType": "Patient",
                "id": patient.identifier,
                "identifier": [{"system": "satusehat", "value": patient.identifier}],
                "name": [{"text": patient.display_name}],
                "active": True,
            },
        )
        rid = str(payload.get("id") or patient.identifier)
        return FhirRef(id=rid, resource_type="Patient")

    async def get_resource(
        self, token: AccessToken, resource_type: str, rid: str
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            join_url(self.base_url, f"{resource_type}/{rid}"),
            token=token.value,
        )
