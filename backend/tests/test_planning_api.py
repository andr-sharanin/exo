"""
E2E tests for Phase 8: /planning/goals endpoints.
"""
import pytest
from httpx import AsyncClient


class TestCreateGoal:
    async def test_create_goal_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/planning/goals", json={
            "title": "Build ExoCortex",
            "horizon": "vision",
        })
        assert r.status_code == 201

    async def test_create_goal_has_required_fields(self, client: AsyncClient) -> None:
        data = (
            await client.post("/api/v1/planning/goals", json={
                "title": "Launch Q1 milestone",
                "horizon": "quarterly",
            })
        ).json()
        assert "id" in data
        assert "title" in data
        assert "horizon" in data
        assert "status" in data
        assert data["status"] == "active"
        assert data["horizon"] == "quarterly"

    async def test_all_six_horizons_accepted(self, client: AsyncClient) -> None:
        horizons = ["vision", "annual", "quarterly", "monthly", "weekly", "daily"]
        for h in horizons:
            r = await client.post("/api/v1/planning/goals", json={
                "title": f"Goal at {h}", "horizon": h,
            })
            assert r.status_code == 201, f"horizon {h!r} was rejected"

    async def test_invalid_horizon_returns_422(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/planning/goals", json={
            "title": "Bad goal", "horizon": "decadal",
        })
        assert r.status_code == 422

    async def test_invalid_parent_hierarchy_returns_422(
        self, client: AsyncClient
    ) -> None:
        # Create a daily goal first
        daily_id = (
            await client.post("/api/v1/planning/goals", json={
                "title": "Daily task", "horizon": "daily",
            })
        ).json()["id"]
        # Try to make a vision goal child of a daily goal — invalid
        r = await client.post("/api/v1/planning/goals", json={
            "title": "Vision under daily?", "horizon": "vision",
            "parent_id": daily_id,
        })
        assert r.status_code == 422


class TestListGoals:
    async def test_list_goals_returns_200(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/planning/goals")
        assert r.status_code == 200

    async def test_list_goals_by_horizon_filters(self, client: AsyncClient) -> None:
        await client.post("/api/v1/planning/goals", json={
            "title": "Annual OKR", "horizon": "annual",
        })
        await client.post("/api/v1/planning/goals", json={
            "title": "Daily focus", "horizon": "daily",
        })
        data = (
            await client.get("/api/v1/planning/goals?horizon=annual")
        ).json()
        assert all(g["horizon"] == "annual" for g in data)


class TestCompleteGoal:
    async def test_complete_goal_returns_200(self, client: AsyncClient) -> None:
        goal_id = (
            await client.post("/api/v1/planning/goals", json={
                "title": "Finish Phase 8", "horizon": "monthly",
            })
        ).json()["id"]
        r = await client.post(f"/api/v1/planning/goals/{goal_id}/complete")
        assert r.status_code == 200

    async def test_complete_goal_changes_status(self, client: AsyncClient) -> None:
        goal_id = (
            await client.post("/api/v1/planning/goals", json={
                "title": "Deploy MVP", "horizon": "quarterly",
            })
        ).json()["id"]
        data = (
            await client.post(f"/api/v1/planning/goals/{goal_id}/complete")
        ).json()
        assert data["status"] == "completed"

    async def test_complete_already_completed_returns_409(
        self, client: AsyncClient
    ) -> None:
        goal_id = (
            await client.post("/api/v1/planning/goals", json={
                "title": "Already done", "horizon": "weekly",
            })
        ).json()["id"]
        await client.post(f"/api/v1/planning/goals/{goal_id}/complete")
        r = await client.post(f"/api/v1/planning/goals/{goal_id}/complete")
        assert r.status_code == 409
