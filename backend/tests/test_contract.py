"""OpenAPI and auth-completeness contracts.

Every private endpoint must reject a request without a bearer token, and every
documented API route must carry a summary and tags for the generated docs.
"""

from __future__ import annotations

import uuid

from app.main import create_app
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

PUBLIC_PATHS = {
    "/api/v1/health/live",
    "/api/v1/health/ready",
    "/api/v1/public/health",
    "/health/live",
    "/health/ready",
    "/public/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/platform-login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/password-reset/request",
    "/api/v1/auth/password-reset/confirm",
    "/api/v1/auth/verify-email/confirm",
    "/api/v1/leads",
    "/api/v1/metrics",
}

PATH_VALUES = {
    "file_id": str(uuid.uuid4()),
    "job_id": str(uuid.uuid4()),
    "user_id": str(uuid.uuid4()),
    "slug": "example-tenant",
}


def _api_routes() -> list[APIRoute]:
    return [
        route
        for route in create_app().routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1")
    ]


async def test_every_private_route_requires_auth() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for route in _api_routes():
            if route.path in PUBLIC_PATHS:
                continue
            path = route.path
            for name, value in PATH_VALUES.items():
                path = path.replace(f"{{{name}}}", value)
            for method in route.methods:
                response = await client.request(method, path)
                assert response.status_code in {401, 403}, (
                    route.path,
                    method,
                    response.status_code,
                    response.text,
                )


def test_openapi_routes_have_summary_and_tags() -> None:
    missing: list[str] = []
    for route in _api_routes():
        if not route.include_in_schema:
            continue
        if not route.summary or not route.tags:
            missing.append(f"{sorted(route.methods)} {route.path}")
    assert missing == []


def test_openapi_document_is_valid() -> None:
    schema = create_app().openapi()
    assert schema["info"]["version"] == "0.1.0"
    assert "/api/v1/users/me" in schema["paths"]
    assert "/api/v1/admin/tenants" in schema["paths"]
    assert "/api/v1/auth/password-reset/request" in schema["paths"]
