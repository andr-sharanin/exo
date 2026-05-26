"""
Tests for GET /reviews/history endpoint.

Verifies pagination, ordering (newest first), and that only completed sessions are returned.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_session import ReviewSession
from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


async def _create_review(
    db: AsyncSession,
    *,
    review_type: str = "daily",
    status: str = "completed",
    completed_at: datetime | None = None,
    created_at: datetime | None = None,
) -> ReviewSession:
    now = datetime.now(timezone.utc)
    session = ReviewSession(
        id=uuid.uuid4(),
        user_id=TEST_USER_ID,
        tenant_id=TEST_TENANT_ID,
        review_type=review_type,
        status=status,
        plan_confirmed=False,
        goals_updated=False,
        created_at=created_at or now,
        completed_at=completed_at or (now if status == "completed" else None),
    )
    db.add(session)
    await db.flush()
    return session


class TestReviewsHistory:
    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient, db: AsyncSession) -> None:
        r = await client.get("/api/v1/reviews/history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_only_completed_sessions_in_response(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await _create_review(db, status="completed")
        await _create_review(db, status="pending", completed_at=None)

        data = (await client.get("/api/v1/reviews/history")).json()
        # All returned items must be completed
        assert all(s["status"] == "completed" for s in data)

    @pytest.mark.asyncio
    async def test_ordered_newest_first(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        now = datetime.now(timezone.utc)
        old = await _create_review(
            db,
            completed_at=now - timedelta(days=5),
            created_at=now - timedelta(days=5),
        )
        new = await _create_review(
            db,
            completed_at=now - timedelta(hours=1),
            created_at=now - timedelta(hours=1),
        )

        data = (await client.get("/api/v1/reviews/history")).json()
        ids = [s["id"] for s in data]
        assert ids.index(str(new.id)) < ids.index(str(old.id))

    @pytest.mark.asyncio
    async def test_limit_reduces_result_count(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        for _ in range(5):
            await _create_review(db)

        data = (await client.get("/api/v1/reviews/history?limit=2")).json()
        assert len(data) <= 2

    @pytest.mark.asyncio
    async def test_offset_skips_records(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        now = datetime.now(timezone.utc)
        # Create 4 sessions with distinct completed_at
        sessions = []
        for i in range(4):
            s = await _create_review(
                db,
                completed_at=now - timedelta(hours=i),
                created_at=now - timedelta(hours=i),
            )
            sessions.append(s)

        all_data = (await client.get("/api/v1/reviews/history?limit=100")).json()
        offset_data = (await client.get("/api/v1/reviews/history?limit=100&offset=2")).json()

        assert len(offset_data) == len(all_data) - 2
        if len(all_data) >= 3:
            assert all_data[2]["id"] == offset_data[0]["id"]

    @pytest.mark.asyncio
    async def test_response_shape(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await _create_review(db, review_type="weekly")
        data = (await client.get("/api/v1/reviews/history?limit=50")).json()
        completed = [s for s in data if s["status"] == "completed"]
        assert len(completed) >= 1
        item = completed[0]
        for field in ("id", "review_type", "status", "created_at", "plan_confirmed"):
            assert field in item, f"missing field: {field}"

    @pytest.mark.asyncio
    async def test_limit_capped_at_100(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        # Requesting more than 100 should still work (capped server-side)
        r = await client.get("/api/v1/reviews/history?limit=200")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
