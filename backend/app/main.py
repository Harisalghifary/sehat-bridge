"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis

from app.auth.router import router as auth_router
from app.config import get_settings
from app.db.engine import make_engine, make_sessionmaker
from app.errors import (
    AppError,
    app_error_handler,
    validation_error_handler,
)
from app.files.router import router as files_router
from app.health import router as health_router
from app.integrations.satusehat.router import router as satusehat_router
from app.tenancy.middleware import TenantMiddleware
from app.users.router import router as users_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.engine = make_engine(settings.database_url)
    app.state.sessionmaker = make_sessionmaker(app.state.engine)
    app.state.redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
    logger.info("startup env=%s version=%s", settings.env, settings.version)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await app.state.engine.dispose()
        logger.info("shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Sehat Bridge API",
        version=settings.version,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(files_router)
    app.include_router(satusehat_router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_middleware(TenantMiddleware)
    return app


app = create_app()
