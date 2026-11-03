"""RFC 7807 problem responses."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

PROBLEM_BASE = "https://sehatbridge.dev/errors"


def problem(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{PROBLEM_BASE}/{code}",
        "title": title,
        "status": status,
        "code": code,
        "trace_id": getattr(request.state, "request_id", None),
        "details": [],
    }
    if detail:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
    )
