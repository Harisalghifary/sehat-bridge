"""Request logging, request ids, metrics, and optional OTLP tracing.

Every request produces exactly one JSON log line (in production) carrying the
same ``request_id`` returned in the ``X-Request-ID`` response header. Values that
look like credentials are scrubbed before a record is written.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram

from app.config import Settings
from app.db.tenant_context import get_tenant
from app.observability_metrics import (  # re-exported for call sites
    AUTH_LOGIN_TOTAL,
    DB_POOL_IN_USE,
    FILE_QUOTA_REJECTIONS_TOTAL,
    FILE_UPLOAD_BYTES_TOTAL,
    TENANT_PROVISION_DURATION,
    TENANT_PROVISION_FAILURES,
)

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="anon")

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["route", "method", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "HTTP requests",
    ["route", "method", "status"],
)

_SCRUB_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)((?:password|client_secret|secret|token|refresh_token|access_token)"
        r"[\"']?\s*[=:]\s*[\"']?)[^\s,\"'}&]+"
    ),
    re.compile(r"(?i)(X-Amz-Signature=)[0-9a-f]+"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
)
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")

_EXTRA_FIELDS = ("request_id", "tenant_slug", "user_id", "client_ip", "route")


def scrub(value: str) -> str:
    for pattern in _SCRUB_PATTERNS:
        if pattern.pattern.startswith("eyJ"):
            value = pattern.sub("[redacted]", value)
        else:
            value = pattern.sub(r"\1[redacted]", value)
    return value


class ScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = scrub(record.getMessage())
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_ctx.get()),
            "tenant_slug": getattr(record, "tenant_slug", None),
            "user_id": getattr(record, "user_id", user_id_ctx.get()),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps({key: value for key, value in payload.items() if value is not None})


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"{self.formatTime(record, '%H:%M:%S')} {record.levelname:<7} "
            f"{record.name} [{getattr(record, 'request_id', request_id_ctx.get())}] "
            f"{record.getMessage()}"
        )
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(ScrubFilter())
    handler.setFormatter(JsonFormatter() if settings.is_prod else TextFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # Our request middleware writes the one access line; silence uvicorn's.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def configure_tracing(settings: Settings) -> None:
    if not settings.otel_exporter_otlp_endpoint:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": "sehat-bridge-api"}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
    )
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer("sehat-bridge")


class ObservabilityMiddleware:
    """Pure ASGI middleware so body-reading middleware can run inside it."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        supplied = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = supplied if _REQUEST_ID.match(supplied) else uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        user_token = user_id_ctx.set("anon")
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        started = time.perf_counter()
        status = 500
        outcome: BaseException | None = None
        span = tracer.start_span("http.request")
        span.set_attribute("http.request_id", request_id)

        async def send_with_header(message: dict[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
                raw = list(message.get("headers", []))
                raw.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": raw}
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        except BaseException as exc:
            outcome = exc
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            route_obj = scope.get("route")
            route = getattr(route_obj, "path", scope.get("path", "unknown"))
            method = scope.get("method", "?")
            current = get_tenant()
            tenant = state.get("tenant_slug") or (current.slug if current is not None else None)
            user_id = state.get("user_id", user_id_ctx.get())
            client_ip = None
            client = scope.get("client")
            if client:
                client_ip = client[0]
            HTTP_REQUEST_DURATION.labels(route, method, str(status)).observe(duration_ms / 1000)
            HTTP_REQUESTS_TOTAL.labels(route, method, str(status)).inc()
            span.set_attribute("http.route", route)
            span.set_attribute("http.method", method)
            span.set_attribute("http.status_code", status)
            if tenant:
                span.set_attribute("tenant_slug", tenant)
            if user_id != "anon":
                span.set_attribute("user_id", user_id)
            if outcome is not None:
                span.record_exception(outcome)
            span.end()
            logging.getLogger("app.request").info(
                "%s %s %s %.1fms",
                method,
                route,
                status,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "tenant_slug": tenant,
                    "user_id": user_id,
                    "client_ip": client_ip,
                },
            )
            request_id_ctx.reset(token)
            user_id_ctx.reset(user_token)


__all__ = [
    "AUTH_LOGIN_TOTAL",
    "DB_POOL_IN_USE",
    "FILE_QUOTA_REJECTIONS_TOTAL",
    "FILE_UPLOAD_BYTES_TOTAL",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION",
    "TENANT_PROVISION_DURATION",
    "TENANT_PROVISION_FAILURES",
    "ObservabilityMiddleware",
    "configure_logging",
    "configure_tracing",
    "request_id_ctx",
    "scrub",
    "user_id_ctx",
]
