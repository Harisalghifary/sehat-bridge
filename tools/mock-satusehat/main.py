"""SATUSEHAT mock: OAuth2 token endpoint and FHIR-shaped resources.

Failure injection is query driven so the outbox can be exercised end to end:

    ?fail=500      retryable server error
    ?fail=4xx      terminal validation error
    ?fail=timeout  slow response (adapter timeout)
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="SATUSEHAT mock", version="0.2.0")

FHIR_PREFIX = "/fhir-r4/v1"


def deterministic_id(resource_type: str, identifier: str) -> str:
    raw = f"{resource_type}|{identifier}".encode()
    return hashlib.sha256(raw).hexdigest()[:24]


def deterministic_token(client_id: str) -> str:
    return hashlib.sha256(f"token|{client_id}".encode()).hexdigest()[:40]


def _operation_outcome(code: str, message: str) -> dict[str, Any]:
    return {
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": code, "diagnostics": message}],
    }


async def _inject(request: Request) -> JSONResponse | None:
    fail = request.query_params.get("fail")
    if fail == "500":
        return JSONResponse(
            status_code=500,
            content=_operation_outcome("exception", "Injected server failure"),
        )
    if fail == "4xx":
        return JSONResponse(
            status_code=400,
            content=_operation_outcome("invalid", "Injected validation failure"),
        )
    if fail == "timeout":
        await asyncio.sleep(8)
        return JSONResponse(
            status_code=504,
            content=_operation_outcome("timeout", "Injected slow response"),
        )
    return None


def _resource_id(resource_type: str, body: dict[str, Any], path_id: str | None) -> str:
    identifiers = body.get("identifier") or []
    identifier = ""
    if identifiers and isinstance(identifiers[0], dict):
        identifier = str(identifiers[0].get("value") or "")
    return path_id or deterministic_id(resource_type, identifier or resource_type)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "mock"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mock-satusehat", "docs": "/docs"}


@app.post("/oauth2/v1/accesstoken")
async def token(request: Request) -> JSONResponse:
    injected = await _inject(request)
    if injected is not None:
        return injected

    form = await request.form()
    client_id = str(form.get("client_id") or "")
    client_secret = str(form.get("client_secret") or "")
    if not client_id or not client_secret:
        return JSONResponse(
            status_code=401,
            content=_operation_outcome(
                "login", "client_id and client_secret are required"
            ),
        )
    return JSONResponse(
        {
            "access_token": deterministic_token(client_id),
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    )


def _authorized(request: Request) -> bool:
    header = request.headers.get("authorization", "")
    return header.startswith("Bearer ") and len(header) > len("Bearer ")


@app.put(FHIR_PREFIX + "/{resource_type}")
@app.put(FHIR_PREFIX + "/{resource_type}/{resource_id}")
async def put_resource(
    resource_type: str,
    request: Request,
    resource_id: str | None = None,
) -> JSONResponse:
    injected = await _inject(request)
    if injected is not None:
        return injected
    if not _authorized(request):
        return JSONResponse(
            status_code=401,
            content=_operation_outcome("login", "Bearer token required"),
        )

    body = await request.json()
    rid = _resource_id(resource_type, body, resource_id)
    resource = dict(body)
    resource["id"] = rid
    resource["resourceType"] = resource_type
    resource["meta"] = {"versionId": "1", "lastUpdated": "2026-01-01T00:00:00Z"}
    return JSONResponse(resource, status_code=200)


@app.get(FHIR_PREFIX + "/{resource_type}/{resource_id}")
async def get_resource(
    resource_type: str, resource_id: str, request: Request
) -> JSONResponse:
    injected = await _inject(request)
    if injected is not None:
        return injected
    if not _authorized(request):
        return JSONResponse(
            status_code=401,
            content=_operation_outcome("login", "Bearer token required"),
        )
    return JSONResponse(
        {
            "resourceType": resource_type,
            "id": resource_id,
            "identifier": [{"system": "satusehat", "value": resource_id}],
            "name": "Mock Organization",
            "active": True,
        }
    )