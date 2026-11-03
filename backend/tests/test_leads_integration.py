"""Public lead capture: abuse controls, dedupe, and validation."""

from __future__ import annotations

import uuid

import asyncpg
import pytest
from app.config import get_settings
from app.db.engine import asyncpg_dsn
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _payload(email: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "name": "dr. Sari",
        "email": email,
        "facility_name": "Klinik Sehat Bersama",
        "facility_type": "klinik",
        "city": "Bandung",
        "phone": "081200000000",
        "message": "Ingin melihat alur integrasi SATUSEHAT",
        "website": "",
        "elapsed_ms": 8000,
    }
    body.update(overrides)
    return body


async def _fetch(sql: str, *args: object) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        return await conn.fetch(sql, *args)
    finally:
        await conn.close()


async def _cleanup(email: str) -> None:
    conn = await asyncpg.connect(asyncpg_dsn(get_settings().migration_database_url))
    try:
        await conn.execute("DELETE FROM public.leads WHERE email = $1", email)
    finally:
        await conn.close()


async def test_valid_lead_is_persisted(api: AsyncClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    email = f"lead-{suffix}@example.com"
    try:
        response = await api.post(
            "/api/v1/leads",
            json=_payload(email),
            headers={"X-Forwarded-For": f"10.{uuid.uuid4().int % 250}.4.1"},
        )
        assert response.status_code == 202, response.text
        assert "Terima kasih" in response.json()["message"]

        rows = await _fetch(
            "SELECT name, facility_name, source, ip::text AS ip FROM public.leads WHERE email = $1",
            email,
        )
        assert len(rows) == 1
        assert rows[0]["facility_name"] == "Klinik Sehat Bersama"
        assert rows[0]["source"] == "website"
    finally:
        await _cleanup(email)


async def test_honeypot_is_accepted_without_a_row(api: AsyncClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    email = f"bot-{suffix}@example.com"
    try:
        response = await api.post(
            "/api/v1/leads",
            json=_payload(email, website="https://spam.example"),
            headers={"X-Forwarded-For": f"10.{uuid.uuid4().int % 250}.4.2"},
        )
        assert response.status_code == 202
        assert await _fetch("SELECT 1 FROM public.leads WHERE email = $1", email) == []
    finally:
        await _cleanup(email)


async def test_too_fast_submission_is_accepted_without_a_row(api: AsyncClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    email = f"fast-{suffix}@example.com"
    try:
        response = await api.post(
            "/api/v1/leads",
            json=_payload(email, elapsed_ms=1200),
            headers={"X-Forwarded-For": f"10.{uuid.uuid4().int % 250}.4.3"},
        )
        assert response.status_code == 202
        assert await _fetch("SELECT 1 FROM public.leads WHERE email = $1", email) == []
    finally:
        await _cleanup(email)


async def test_duplicate_within_24h_updates_the_same_lead(api: AsyncClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    email = f"dup-{suffix}@example.com"
    ip = f"10.{uuid.uuid4().int % 250}.4.4"
    try:
        first = await api.post(
            "/api/v1/leads",
            json=_payload(email),
            headers={"X-Forwarded-For": ip},
        )
        second = await api.post(
            "/api/v1/leads",
            json=_payload(email, message="Pesan kedua"),
            headers={"X-Forwarded-For": ip},
        )
        assert first.status_code == 202
        assert second.status_code == 202

        rows = await _fetch("SELECT message FROM public.leads WHERE email = $1", email)
        assert len(rows) == 1
        assert rows[0]["message"] == "Pesan kedua"
    finally:
        await _cleanup(email)


async def test_ip_rate_limit_returns_429(api: AsyncClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    ip = f"10.{uuid.uuid4().int % 250}.4.5"
    emails = [f"rate-{suffix}-{index}@example.com" for index in range(6)]
    try:
        for email in emails[:5]:
            response = await api.post(
                "/api/v1/leads",
                json=_payload(email),
                headers={"X-Forwarded-For": ip},
            )
            assert response.status_code == 202, response.text

        blocked = await api.post(
            "/api/v1/leads",
            json=_payload(emails[5]),
            headers={"X-Forwarded-For": ip},
        )
        assert blocked.status_code == 429
        assert blocked.json()["code"] == "rate_limited"
        assert blocked.headers["retry-after"]
    finally:
        for email in emails:
            await _cleanup(email)


async def test_invalid_email_is_rejected(api: AsyncClient) -> None:
    response = await api.post(
        "/api/v1/leads",
        json=_payload("not-an-email"),
        headers={"X-Forwarded-For": f"10.{uuid.uuid4().int % 250}.4.6"},
    )
    assert response.status_code == 422
