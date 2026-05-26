"""
E2E tests for Phase 6: /admin/* endpoints.
Admin endpoints require the "admin" role — tests use a local admin_client fixture.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenClaims, get_current_user
from app.core.database import get_db
from app.core.rls import get_tenant_db
from app.main import app
from tests.conftest import TEST_TENANT_ID, TEST_USER_ID

_ADMIN_USER = TokenClaims(
    sub=str(TEST_USER_ID),
    user_id=TEST_USER_ID,
    tenant_id=TEST_TENANT_ID,
    email="admin@exocortex.test",
    roles=["user", "admin"],
)


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession) -> AsyncClient:
    """Client authenticated as an admin-role user."""
    async def _override_db():
        yield db

    async def _override_auth():
        return _ADMIN_USER

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_tenant_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_auth

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


class TestAdminHealth:
    async def test_health_returns_200_for_admin(
        self, admin_client: AsyncClient
    ) -> None:
        r = await admin_client.get("/api/v1/admin/health")
        assert r.status_code == 200

    async def test_health_response_has_required_fields(
        self, admin_client: AsyncClient
    ) -> None:
        data = (await admin_client.get("/api/v1/admin/health")).json()
        assert "status" in data
        assert "ai_tiers" in data
        assert "timestamp" in data

    async def test_health_non_admin_returns_403(
        self, client: AsyncClient
    ) -> None:
        # regular `client` fixture has roles=["user"]
        r = await client.get("/api/v1/admin/health")
        assert r.status_code == 403


class TestAdminAudit:
    async def test_audit_returns_200_for_admin(
        self, admin_client: AsyncClient
    ) -> None:
        r = await admin_client.get("/api/v1/admin/audit")
        assert r.status_code == 200

    async def test_audit_returns_paginated_structure(
        self, admin_client: AsyncClient
    ) -> None:
        data = (await admin_client.get("/api/v1/admin/audit")).json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    async def test_audit_non_admin_returns_403(
        self, client: AsyncClient
    ) -> None:
        r = await client.get("/api/v1/admin/audit")
        assert r.status_code == 403


class TestAdminAIStats:
    async def test_ai_stats_returns_200(
        self, admin_client: AsyncClient
    ) -> None:
        r = await admin_client.get("/api/v1/admin/ai-stats")
        assert r.status_code == 200

    async def test_ai_stats_structure(
        self, admin_client: AsyncClient
    ) -> None:
        data = (await admin_client.get("/api/v1/admin/ai-stats")).json()
        assert "total_requests" in data
        assert "by_tier" in data
        assert "success_rate" in data

    async def test_ai_stats_non_admin_returns_403(
        self, client: AsyncClient
    ) -> None:
        r = await client.get("/api/v1/admin/ai-stats")
        assert r.status_code == 403
