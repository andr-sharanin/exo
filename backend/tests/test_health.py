from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    with _mock_external_services():
        response = await client.get("/api/v1/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_schema(client: AsyncClient) -> None:
    with _mock_external_services():
        response = await client.get("/api/v1/health")

    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "checks" in data
    assert set(data["checks"].keys()) == {"database", "redis", "keycloak"}


@pytest.mark.asyncio
async def test_health_database_ok(client: AsyncClient) -> None:
    with _mock_external_services():
        response = await client.get("/api/v1/health")

    assert response.json()["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_health_degraded_when_redis_down(client: AsyncClient) -> None:
    with _mock_external_services(redis_ok=False):
        response = await client.get("/api/v1/health")

    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["redis"].startswith("error:")


@pytest.mark.asyncio
async def test_health_degraded_when_keycloak_down(client: AsyncClient) -> None:
    with _mock_external_services(keycloak_ok=False):
        response = await client.get("/api/v1/health")

    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["keycloak"].startswith("error:")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_external_services(*, redis_ok: bool = True, keycloak_ok: bool = True):
    """Context manager patching Redis and Keycloak calls for unit tests."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        redis_patch = patch("app.api.v1.health.aioredis.from_url")
        httpx_patch = patch("app.api.v1.health.httpx.AsyncClient")

        with redis_patch as mock_redis, httpx_patch as mock_httpx:
            # Redis mock
            mock_redis_instance = AsyncMock()
            if redis_ok:
                mock_redis_instance.ping = AsyncMock(return_value=True)
            else:
                mock_redis_instance.ping = AsyncMock(side_effect=ConnectionError("refused"))
            mock_redis_instance.aclose = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Keycloak mock
            mock_http_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200 if keycloak_ok else 503
            mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_http_instance.__aexit__ = AsyncMock(return_value=None)
            if keycloak_ok:
                mock_http_instance.get = AsyncMock(return_value=mock_response)
            else:
                mock_http_instance.get = AsyncMock(
                    side_effect=ConnectionError("keycloak unreachable")
                )
            mock_httpx.return_value = mock_http_instance

            yield

    return _ctx()
