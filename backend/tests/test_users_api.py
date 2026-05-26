"""
E2E tests for Users API — GDPR data export and account deletion.

GET    /users/me/export   → 200 with data snapshot
DELETE /users/me          → 204 (with correct header) or 400 (wrong/missing header)
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import HabitDefinition
from app.models.planning_goal import PlanningGoal
from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


class TestDataExport:
    async def test_export_returns_200(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/users/me/export")
        assert r.status_code == 200

    async def test_export_has_required_top_level_keys(self, client: AsyncClient) -> None:
        data = (await client.get("/api/v1/users/me/export")).json()
        expected = {
            "exported_at", "user_id", "tenant_id",
            "energy_scores", "system_modes", "day_plans",
            "planning_goals", "commitment_deposits",
            "habits", "habit_entries", "onboarding_sessions",
            "review_sessions", "behavioral_events_count",
        }
        assert expected.issubset(data.keys())

    async def test_export_user_id_matches_token(self, client: AsyncClient) -> None:
        data = (await client.get("/api/v1/users/me/export")).json()
        assert data["user_id"] == str(TEST_USER_ID)

    async def test_export_returns_lists_for_collection_fields(
        self, client: AsyncClient
    ) -> None:
        data = (await client.get("/api/v1/users/me/export")).json()
        for key in ("energy_scores", "habits", "planning_goals"):
            assert isinstance(data[key], list), f"{key} should be a list"

    async def test_export_behavioral_events_count_is_int(
        self, client: AsyncClient
    ) -> None:
        data = (await client.get("/api/v1/users/me/export")).json()
        assert isinstance(data["behavioral_events_count"], int)


class TestAccountDeletion:
    async def test_delete_without_header_returns_422(
        self, client: AsyncClient
    ) -> None:
        r = await client.delete("/api/v1/users/me")
        # FastAPI returns 422 for missing required header
        assert r.status_code == 422

    async def test_delete_with_wrong_header_returns_400(
        self, client: AsyncClient
    ) -> None:
        r = await client.delete(
            "/api/v1/users/me",
            headers={"X-Confirm-Delete": "yes please"},
        )
        assert r.status_code == 400

    async def test_delete_with_correct_header_returns_204(
        self, client: AsyncClient
    ) -> None:
        r = await client.delete(
            "/api/v1/users/me",
            headers={"X-Confirm-Delete": "DELETE MY ACCOUNT"},
        )
        assert r.status_code == 204

    async def test_delete_deactivates_habits(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        habit = HabitDefinition(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            title="Morning run",
            frequency="daily",
            is_active=True,
        )
        db.add(habit)
        await db.flush()

        await client.delete(
            "/api/v1/users/me",
            headers={"X-Confirm-Delete": "DELETE MY ACCOUNT"},
        )

        await db.refresh(habit)
        assert habit.is_active is False

    async def test_delete_abandons_active_goals(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        goal = PlanningGoal(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            title="Launch ExoCortex",
            horizon="month",
            status="active",
        )
        db.add(goal)
        await db.flush()

        await client.delete(
            "/api/v1/users/me",
            headers={"X-Confirm-Delete": "DELETE MY ACCOUNT"},
        )

        await db.refresh(goal)
        assert goal.status == "abandoned"
