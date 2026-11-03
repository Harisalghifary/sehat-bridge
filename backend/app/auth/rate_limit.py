"""Fixed-window rate limiting backed by Redis.

If Redis is unreachable the limiter allows the request and logs; failing closed
would turn a cache outage into a full login outage.
"""

from __future__ import annotations

import logging
from typing import Any

from app.errors import AppError

logger = logging.getLogger(__name__)


async def enforce(
    redis: Any,
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        if count > limit:
            ttl = await redis.ttl(key)
            retry_after = max(int(ttl), 1)
            raise AppError(
                status=429,
                code="rate_limited",
                title="Too many requests",
                detail=f"Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )
    except AppError:
        raise
    except Exception:
        logger.warning("rate limiter unavailable", exc_info=True)


def client_ip(request: Any) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
