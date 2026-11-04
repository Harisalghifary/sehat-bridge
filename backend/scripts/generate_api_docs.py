"""Generate docs/api.md from the live FastAPI schema."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app

TARGET = Path(__file__).resolve().parents[2] / "docs" / "api.md"
PUBLIC = {
    "/api/v1/health/live",
    "/api/v1/health/ready",
    "/api/v1/public/health",
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


def main() -> None:
    app = create_app()
    schema = app.openapi()
    lines = [
        "# API reference",
        "",
        "Generated from the running FastAPI schema by "
        "`cd backend && uv run python scripts/generate_api_docs.py`.",
        "Do not hand-edit. Swagger UI is at `/api/docs`.",
        "",
        "Base path `/api/v1`. Errors use `application/problem+json` with "
        "`type`, `title`, `status`, `code`, `trace_id`, and `details`.",
        "Send `Authorization: Bearer <access_token>` on every row marked private.",
        "Send `Idempotency-Key` on mutating requests to make retries safe.",
        "",
        "| Method | Path | Auth | Summary |",
        "|---|---|---|---|",
    ]
    rows: list[tuple[str, str, str, str]] = []
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            auth = "public" if path in PUBLIC else "private"
            summary = operation.get("summary", "")
            rows.append((method.upper(), path, auth, summary))
    rows.sort(key=lambda row: (row[1], row[0]))
    for method, path, auth, summary in rows:
        lines.append(f"| {method} | `{path}` | {auth} | {summary} |")
    lines.extend(
        [
            "",
            "## Error codes",
            "",
            "See `docs/04-api-spec.md §6`. Every problem body includes the same "
            "`request_id` returned in the `X-Request-ID` response header.",
            "",
            "## Generation",
            "",
            "```bash",
            "cd backend && uv run python scripts/generate_api_docs.py",
            "```",
            "",
        ]
    )
    TARGET.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
