"""Adapter selection by configuration only."""

from __future__ import annotations

from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.integrations.satusehat.live import LiveAdapter
from app.integrations.satusehat.mock import MockAdapter
from app.integrations.satusehat.port import SatusehatPort


def base_url_for_mode(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if settings.satusehat_mode == "live":
        return f"{settings.satusehat_live_url.rstrip('/')}/fhir-r4/v1"
    return f"{settings.satusehat_mock_url.rstrip('/')}/fhir-r4/v1"


def build_adapter(
    redis: Redis | None = None,
    settings: Settings | None = None,
    *,
    base_url: str | None = None,
) -> SatusehatPort:
    settings = settings or get_settings()
    resolved = base_url or base_url_for_mode(settings)
    if settings.satusehat_mode == "live":
        return LiveAdapter(resolved, redis=redis, timeout=settings.satusehat_timeout_seconds)
    return MockAdapter(resolved, timeout=settings.satusehat_timeout_seconds)
