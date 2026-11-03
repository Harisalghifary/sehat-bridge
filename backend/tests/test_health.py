import pytest
from app import health
from httpx import AsyncClient


async def test_live_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_live_alias_under_api_prefix(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["version"]


async def test_public_health_is_minimal(client: AsyncClient) -> None:
    for path in ("/public/health", "/api/v1/public/health"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "checks" not in response.json()


async def test_ready_reports_each_dependency(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok(_request: object) -> str:
        return "ok"

    monkeypatch.setattr(health, "check_postgres", ok)
    monkeypatch.setattr(health, "check_redis", ok)
    monkeypatch.setattr(health, "check_minio", ok)

    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["checks"] == {
        "postgres": "ok",
        "redis": "ok",
        "minio": "ok",
    }


async def test_ready_is_503_when_a_dependency_fails(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok(_request: object) -> str:
        return "ok"

    async def broken(_request: object) -> str:
        return "error"

    monkeypatch.setattr(health, "check_postgres", ok)
    monkeypatch.setattr(health, "check_redis", broken)
    monkeypatch.setattr(health, "check_minio", ok)

    response = await client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"] == "error"
    assert "sehat@" not in response.text


def test_verdict_requires_every_check() -> None:
    assert health.verdict({"a": "ok", "b": "ok"}) is True
    assert health.verdict({"a": "ok", "b": "error"}) is False
