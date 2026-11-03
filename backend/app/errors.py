"""RFC 7807 problem responses."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PROBLEM_BASE = "https://sehatbridge.dev/errors"


class AppError(Exception):
    def __init__(
        self,
        *,
        status: int,
        code: str,
        title: str,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(title)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.headers = headers
        self.extra = extra


def _body(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    details: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": f"{PROBLEM_BASE}/{code}",
        "title": title,
        "status": status,
        "code": code,
        "trace_id": getattr(request.state, "request_id", None),
        "details": details or [],
    }
    if detail:
        body["detail"] = detail
    if extra:
        body.update(extra)
    return body


def problem(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    **extra: Any,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=_body(request, status=status, code=code, title=title, detail=detail, extra=extra),
        media_type="application/problem+json",
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):
        raise exc
    return JSONResponse(
        status_code=exc.status,
        content=_body(
            request,
            status=exc.status,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            extra=exc.extra or None,
        ),
        media_type="application/problem+json",
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"][1:]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_body(
            request,
            status=422,
            code="validation_error",
            title="Request validation failed",
            details=details,
        ),
        media_type="application/problem+json",
    )
