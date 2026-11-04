"""Request ids, structured log fields, and secret scrubbing."""

from __future__ import annotations

import logging

from app.observability import scrub
from httpx import AsyncClient


def test_scrubber_removes_tokens_and_secrets() -> None:
    value = (
        "Authorization: Bearer abc.def.ghi password=hunter2 client_secret=s3cret "
        "X-Amz-Signature=deadbeef"
    )
    cleaned = scrub(value)
    assert "hunter2" not in cleaned
    assert "s3cret" not in cleaned
    assert "deadbeef" not in cleaned
    assert "[redacted]" in cleaned


async def test_request_id_is_returned_and_logged(client: AsyncClient, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    assert len(request_id) >= 8

    records = [record for record in caplog.records if record.name == "app.request"]
    assert len(records) == 1
    assert records[0].request_id == request_id
    assert "GET" in records[0].getMessage()
