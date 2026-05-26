"""
E2E tests for Phase 7: /secretary/* endpoints.
No StepObjects needed — generate works with empty plan.
"""
import pytest
from httpx import AsyncClient


class TestPlanGeneration:
    async def test_generate_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/secretary/plan")
        assert r.status_code == 201

    async def test_generate_response_has_required_fields(
        self, client: AsyncClient
    ) -> None:
        data = (await client.post("/api/v1/secretary/plan")).json()
        assert "id" in data
        assert "plan_date" in data
        assert "status" in data
        assert "items" in data
        assert "total_estimated_minutes" in data
        assert data["status"] == "draft"

    async def test_generate_empty_when_no_steps(self, client: AsyncClient) -> None:
        data = (await client.post("/api/v1/secretary/plan")).json()
        assert data["items"] == []
        assert data["total_estimated_minutes"] == 0

    async def test_get_today_after_generate_returns_200(
        self, client: AsyncClient
    ) -> None:
        await client.post("/api/v1/secretary/plan")
        r = await client.get("/api/v1/secretary/plan/today")
        assert r.status_code == 200

    async def test_get_today_before_generate_returns_404(
        self, client: AsyncClient
    ) -> None:
        r = await client.get("/api/v1/secretary/plan/today")
        assert r.status_code == 404


class TestPlanAccept:
    async def test_accept_draft_plan_returns_200(self, client: AsyncClient) -> None:
        plan_id = (await client.post("/api/v1/secretary/plan")).json()["id"]
        r = await client.post(f"/api/v1/secretary/plan/{plan_id}/accept")
        assert r.status_code == 200

    async def test_accept_changes_status_to_accepted(
        self, client: AsyncClient
    ) -> None:
        plan_id = (await client.post("/api/v1/secretary/plan")).json()["id"]
        data = (
            await client.post(f"/api/v1/secretary/plan/{plan_id}/accept")
        ).json()
        assert data["status"] == "accepted"

    async def test_accept_already_accepted_plan_returns_409(
        self, client: AsyncClient
    ) -> None:
        plan_id = (await client.post("/api/v1/secretary/plan")).json()["id"]
        await client.post(f"/api/v1/secretary/plan/{plan_id}/accept")
        r = await client.post(f"/api/v1/secretary/plan/{plan_id}/accept")
        assert r.status_code == 409
