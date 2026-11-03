"""Liveness and readiness probes.

Readiness reports each dependency independently. A failure never leaks an
exception message or a connection string — only the dependency name and state.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

import httpx
from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

CheckState = Literal["ok", "error"]

TIMEOUT_SECONDS = 2.0


async def check_postgres(request: Request) -> CheckState:
    try:
        async with request.app.state.engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("select 1")), TIMEOUT_SECONDS)
        return "ok"
    except Exception:
        logger.warning("readiness: postgres check failed", exc_info=True)
        return "error"


async def check_redis(request: Request) -> CheckState:
    try:
        await asyncio.wait_for(request.app.state.redis.ping(), TIMEOUT_SECONDS)
        return "ok"
    except Exception:
        logger.warning("readiness: redis check failed", exc_info=True)
        return "error"


async def check_minio(request: Request) -> CheckState:
    settings = get_settings()
    url = f"{settings.minio_endpoint.rstrip('/')}/minio/health/live"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
            return "ok" if resp.status_code == 200 else "error"
    except Exception:
        logger.warning("readiness: minio check failed", exc_info=True)
        return "error"


def verdict(checks: dict[str, CheckState]) -> bool:
    return all(state == "ok" for state in checks.values())


@router.get("/health/live")
@router.get("/api/v1/health/live")
async def live() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": settings.version}


@router.get("/public/health")
@router.get("/api/v1/public/health")
async def public_health() -> dict[str, str]:
    """Minimal, unauthenticated status for the marketing site."""
    settings = get_settings()
    return {"status": "ok", "version": settings.version}


@router.get("/health/ready")
@router.get("/api/v1/health/ready")
async def ready(request: Request, response: Response) -> dict[str, object]:
    settings = get_settings()
    checks = {
        "postgres": await check_postgres(request),
        "redis": await check_redis(request),
        "minio": await check_minio(request),
    }
    ok = verdict(checks)
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if ok else "degraded",
        "version": settings.version,
        "checks": checks,
    }
