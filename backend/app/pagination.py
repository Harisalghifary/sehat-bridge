"""Opaque keyset cursors for newest-first lists."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from app.errors import AppError


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    payload = json.dumps({"t": created_at.isoformat(), "id": str(item_id)})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
        return datetime.fromisoformat(payload["t"]), UUID(payload["id"])
    except Exception as exc:
        raise AppError(
            status=422,
            code="invalid_cursor",
            title="Invalid cursor",
        ) from exc
