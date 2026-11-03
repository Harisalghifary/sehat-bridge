"""Deterministic local SATUSEHAT adapter."""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

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


def deterministic_id(resource_type: str, identifier: str) -> str:
    """Same input -> same FHIR id, across processes and restarts."""
    raw = f"{resource_type}|{identifier}".encode()
    return hashlib.sha256(raw).hexdigest()[:24]


def deterministic_token(client_id: str) -> str:
    return hashlib.sha256(f"token|{client_id}".encode()).hexdigest()[:40]


class MockAdapter:
    def __init__(self, base_url: str, *, timeout: float = 10.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        url: str,
        *,
        token: AccessToken | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/fhir+json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token.value}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=headers, json=json, data=data)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise SatusehatError(f"Mock transport failure: {exc}", retryable=True) from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = {"raw": response.text[:500]}
            raise SatusehatError(
                f"Mock returned HTTP {response.status_code}",
                status_code=response.status_code,
                retryable=retryable_status(response.status_code),
                body=body,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise SatusehatError("Mock returned a non-JSON response", retryable=True) from exc
        return dict(payload)

    async def issue_token(self, creds: Credentials) -> AccessToken:
        payload = await self._request(
            "POST",
            f"{origin_url(creds.base_url)}/oauth2/v1/accesstoken",
            data={
                "grant_type": "client_credentials",
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
            },
        )
        return AccessToken(
            value=str(payload["access_token"]),
            expires_in=int(payload.get("expires_in", 3600)),
        )

    async def put_organization(self, token: AccessToken, org: OrganizationDraft) -> FhirRef:
        payload = await self._request(
            "PUT",
            join_url(self.base_url, "Organization"),
            token=token,
            json={
                "resourceType": "Organization",
                "identifier": [{"system": "satusehat", "value": org.identifier}],
                "name": org.name,
                "active": True,
            },
        )
        rid = str(payload.get("id") or deterministic_id("Organization", org.identifier))
        return FhirRef(id=rid, resource_type="Organization")

    async def put_patient(self, token: AccessToken, patient: PatientDraft) -> FhirRef:
        payload = await self._request(
            "PUT",
            join_url(self.base_url, "Patient"),
            token=token,
            json={
                "resourceType": "Patient",
                "identifier": [{"system": "satusehat", "value": patient.identifier}],
                "name": [{"text": patient.display_name}],
                "active": True,
            },
        )
        rid = str(payload.get("id") or deterministic_id("Patient", patient.identifier))
        return FhirRef(id=rid, resource_type="Patient")

    async def get_resource(
        self, token: AccessToken, resource_type: str, rid: str
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            join_url(self.base_url, f"{resource_type}/{rid}"),
            token=token,
        )
