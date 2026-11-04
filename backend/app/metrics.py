"""Prometheus scrape endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import get_settings
from app.errors import AppError
from app.observability import DB_POOL_IN_USE

router = APIRouter(tags=["observability"])


@router.get("/api/v1/metrics", summary="Prometheus metrics")
async def metrics(request: Request) -> Response:
    settings = get_settings()
    if not settings.metrics_enabled:
        raise AppError(status=404, code="not_found", title="Not found")
    if settings.metrics_token:
        header = request.headers.get("authorization", "")
        if header != f"Bearer {settings.metrics_token}":
            raise AppError(status=401, code="invalid_token", title="Not authenticated")

    pool = getattr(request.app.state, "engine", None)
    if pool is not None:
        DB_POOL_IN_USE.set(pool.pool.checkedout())
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
