"""Resolve the tenant from the routing hint and bind it to the request."""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.db.tenant_context import current_tenant
from app.errors import problem
from app.tenancy.service import resolve_tenant

logger = logging.getLogger(__name__)

TENANT_HEADER = "x-tenant-id"


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        slug = request.headers.get(TENANT_HEADER)
        token = current_tenant.set(None)
        try:
            if slug:
                tenant = await resolve_tenant(
                    getattr(request.app.state, "redis", None),
                    request.app.state.engine,
                    slug,
                )
                if tenant is None:
                    return problem(
                        request,
                        status=404,
                        code="tenant_not_found",
                        title="Tenant not found",
                        detail=f"No tenant with slug {slug!r}",
                    )
                if tenant.status != "active":
                    return problem(
                        request,
                        status=403,
                        code="tenant_inactive",
                        title="Tenant is not active",
                        detail=f"Tenant status is {tenant.status}",
                    )
                request.state.tenant = tenant
                request.state.tenant_slug = tenant.slug
                current_tenant.set(tenant)
            return await call_next(request)
        finally:
            current_tenant.reset(token)
