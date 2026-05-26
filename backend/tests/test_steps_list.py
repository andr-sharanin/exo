"""
Tests for GET /steps endpoint.

Returns active (non-terminal) StepObjects for the current user.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.step_object import StepObject
from app.repositories.pipeline_repos import StepObjectRepo
from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


def _make_step(title: str = "Do the thing") -> StepObject:
    return StepObject(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        user_id=TEST_USER_ID,
        decision_id=uuid.uuid4(),
        step_type="focus_step",
        execution_readiness="ready",
        title=title,
        status="pending",
        step_order=1,
        estimated_minutes=30,
    )


class TestListSteps:
    @pytest.mark.asyncio
    async def test_returns_200_with_empty_list(self, client: AsyncClient) -> None:
        with patch.object(StepObjectRepo, "list_active_for_user", new=AsyncMock(return_value=[])):
            r = await client.get("/api/v1/steps")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_returns_step_list(self, client: AsyncClient) -> None:
        step = _make_step("Write unit tests")
        with patch.object(StepObjectRepo, "list_active_for_user", new=AsyncMock(return_value=[step])):
            r = await client.get("/api/v1/steps")

        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Write unit tests"
        assert data[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_returns_multiple_steps(self, client: AsyncClient) -> None:
        steps = [_make_step(f"Step {i}") for i in range(3)]
        with patch.object(StepObjectRepo, "list_active_for_user", new=AsyncMock(return_value=steps)):
            r = await client.get("/api/v1/steps")

        assert r.status_code == 200
        assert len(r.json()) == 3

    @pytest.mark.asyncio
    async def test_response_contains_required_fields(self, client: AsyncClient) -> None:
        step = _make_step("Fix bug")
        with patch.object(StepObjectRepo, "list_active_for_user", new=AsyncMock(return_value=[step])):
            data = (await client.get("/api/v1/steps")).json()

        assert len(data) == 1
        item = data[0]
        for field in ("id", "title", "status", "step_type"):
            assert field in item, f"missing field: {field}"

    @pytest.mark.asyncio
    async def test_only_active_statuses_returned(self, client: AsyncClient) -> None:
        # Repo already filters — test that the endpoint faithfully passes through
        steps = [
            _make_step("A"),
            _make_step("B"),
        ]
        steps[0].status = "in_progress"
        steps[1].status = "ready"

        with patch.object(StepObjectRepo, "list_active_for_user", new=AsyncMock(return_value=steps)):
            data = (await client.get("/api/v1/steps")).json()

        statuses = {s["status"] for s in data}
        assert "in_progress" in statuses or "ready" in statuses
        assert "completed" not in statuses
        assert "cancelled" not in statuses
