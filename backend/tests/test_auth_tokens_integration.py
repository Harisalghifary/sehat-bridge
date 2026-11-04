"""Email verification and password reset with single-use tokens."""

from __future__ import annotations

import re

import pytest
from app.auth import tokens as token_service
from app.db.tenant_context import TenantContext
from httpx import AsyncClient

from tests.conftest import PASSWORD

pytestmark = pytest.mark.integration

LINK_TOKEN = re.compile(r"token=([A-Za-z0-9_-]+)")


async def _login(api: AsyncClient, slug: str, email: str, password: str = PASSWORD):
    return await api.post(
        "/api/v1/auth/login",
        json={"tenant_slug": slug, "email": email, "password": password},
    )


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, str]]:
    messages: list[tuple[str, str, str]] = []

    async def fake_send(*, to: str, subject: str, text: str) -> bool:
        messages.append((to, subject, text))
        return True

    monkeypatch.setattr(token_service, "send_email", fake_send)
    return messages


async def test_verify_email_then_confirm(
    api: AsyncClient, tenant: tuple[TenantContext, str], outbox: list[tuple[str, str, str]]
) -> None:
    current, email = tenant
    login = await _login(api, current.slug, email)
    token = login.json()["access_token"]
    headers = {"authorization": f"Bearer {token}", "x-tenant-id": current.slug}

    sent = await api.post("/api/v1/auth/verify-email", headers=headers)
    assert sent.status_code == 202, sent.text
    assert len(outbox) == 1
    match = LINK_TOKEN.search(outbox[0][2])
    assert match is not None

    confirmed = await api.post("/api/v1/auth/verify-email/confirm", json={"token": match.group(1)})
    assert confirmed.status_code == 200, confirmed.text

    me = await api.get("/api/v1/users/me", headers=headers)
    assert me.json()["is_verified"] is True

    again = await api.post("/api/v1/auth/verify-email/confirm", json={"token": match.group(1)})
    assert again.status_code == 400
    assert again.json()["code"] == "invalid_verification_token"


async def test_password_reset_is_single_use_and_revokes_sessions(
    api: AsyncClient, tenant: tuple[TenantContext, str], outbox: list[tuple[str, str, str]]
) -> None:
    current, email = tenant
    login = await _login(api, current.slug, email)
    assert login.status_code == 200
    old_refresh = login.json()["refresh_token"]

    requested = await api.post("/api/v1/auth/password-reset/request", json={"email": email})
    assert requested.status_code == 202, requested.text
    assert requested.json()["message"] == "If the address exists, a link was sent."
    assert len(outbox) == 1
    match = LINK_TOKEN.search(outbox[0][2])
    assert match is not None

    new_password = "brand-new-password-456"
    confirmed = await api.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": match.group(1), "new_password": new_password},
    )
    assert confirmed.status_code == 200, confirmed.text

    assert (await _login(api, current.slug, email)).status_code == 401
    assert (await _login(api, current.slug, email, new_password)).status_code == 200

    reused = await api.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": match.group(1), "new_password": "another-password-789"},
    )
    assert reused.status_code == 400
    assert reused.json()["code"] == "invalid_reset_token"

    # Existing refresh tokens are revoked by a reset.
    refreshed = await api.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 401


async def test_unknown_reset_request_still_202(
    api: AsyncClient, outbox: list[tuple[str, str, str]]
) -> None:
    response = await api.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 202
    assert response.json()["message"] == "If the address exists, a link was sent."
    assert outbox == []
