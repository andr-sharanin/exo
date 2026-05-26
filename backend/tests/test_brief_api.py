"""
E2E tests for Morning Brief API.

GET  /brief/today      — returns cached brief (200) or enqueues + 202
POST /brief/regenerate — invalidates cache, always 202
"""
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.secretary import get_arq
from app.main import app


def _arq_override(enqueue_return=None):
    """Returns a FastAPI dependency override that yields a mock ARQ client."""
    mock = AsyncMock()
    mock.enqueue_job = AsyncMock(return_value=enqueue_return or MagicMock())

    async def _dep():
        return mock

    return _dep, mock


class TestGetTodayBrief:
    async def test_returns_cached_brief_when_present(
        self, client: AsyncClient
    ) -> None:
        today = date.today().isoformat()
        cached = {
            "greeting": "Добро утро!",
            "bullets": [{"emoji": "🎯", "text": "Focus"}],
            "focus_recommendation": "Do it.",
            "energy_tip": "Sleep.",
            "date": today,
            "generated_at": "2026-05-25T06:00:00+00:00",
        }

        dep, _ = _arq_override()
        app.dependency_overrides[get_arq] = dep

        mock_svc = MagicMock()
        mock_svc.get_cached = AsyncMock(return_value=cached)

        try:
            with (
                patch("app.api.v1.brief.MorningBriefService", return_value=mock_svc),
                patch("app.api.v1.brief.get_redis_pool", return_value=MagicMock()),
                patch("redis.asyncio.Redis", return_value=MagicMock()),
            ):
                r = await client.get("/api/v1/brief/today")
        finally:
            app.dependency_overrides.pop(get_arq, None)

        assert r.status_code == 200
        data = r.json()
        assert data["greeting"] == "Добро утро!"
        assert "bullets" in data

    async def test_returns_202_when_not_cached(self, client: AsyncClient) -> None:
        dep, mock_arq = _arq_override()
        app.dependency_overrides[get_arq] = dep

        mock_svc = MagicMock()
        mock_svc.get_cached = AsyncMock(return_value=None)

        try:
            with (
                patch("app.api.v1.brief.MorningBriefService", return_value=mock_svc),
                patch("app.api.v1.brief.get_redis_pool", return_value=MagicMock()),
                patch("redis.asyncio.Redis", return_value=MagicMock()),
            ):
                r = await client.get("/api/v1/brief/today")
        finally:
            app.dependency_overrides.pop(get_arq, None)

        assert r.status_code == 202
        data = r.json()
        assert data["status"] == "generating"
        assert "job_id" in data

    async def test_202_response_has_queued_field(
        self, client: AsyncClient
    ) -> None:
        dep, _ = _arq_override()
        app.dependency_overrides[get_arq] = dep

        mock_svc = MagicMock()
        mock_svc.get_cached = AsyncMock(return_value=None)

        try:
            with (
                patch("app.api.v1.brief.MorningBriefService", return_value=mock_svc),
                patch("app.api.v1.brief.get_redis_pool", return_value=MagicMock()),
                patch("redis.asyncio.Redis", return_value=MagicMock()),
            ):
                data = (await client.get("/api/v1/brief/today")).json()
        finally:
            app.dependency_overrides.pop(get_arq, None)

        assert "queued" in data
        assert "message" in data


class TestRegenerateBrief:
    async def test_returns_202_with_job_id(self, client: AsyncClient) -> None:
        dep, _ = _arq_override()
        app.dependency_overrides[get_arq] = dep

        mock_svc = MagicMock()
        mock_svc.invalidate = AsyncMock(return_value=None)

        try:
            with (
                patch("app.api.v1.brief.MorningBriefService", return_value=mock_svc),
                patch("app.api.v1.brief.get_redis_pool", return_value=MagicMock()),
                patch("redis.asyncio.Redis", return_value=MagicMock()),
            ):
                r = await client.post("/api/v1/brief/regenerate")
        finally:
            app.dependency_overrides.pop(get_arq, None)

        assert r.status_code == 202
        data = r.json()
        assert data["status"] == "queued"
        assert "job_id" in data

    async def test_invalidate_called_before_enqueue(
        self, client: AsyncClient
    ) -> None:
        call_order: list[str] = []

        dep, mock_arq = _arq_override()
        app.dependency_overrides[get_arq] = dep

        mock_svc = MagicMock()

        async def _record_invalidate(user_id: str) -> None:
            call_order.append("invalidate")

        mock_svc.invalidate = _record_invalidate

        original_enqueue = mock_arq.enqueue_job

        async def _record_enqueue(*args, **kwargs):
            call_order.append("enqueue")
            return MagicMock()

        mock_arq.enqueue_job = _record_enqueue

        try:
            with (
                patch("app.api.v1.brief.MorningBriefService", return_value=mock_svc),
                patch("app.api.v1.brief.get_redis_pool", return_value=MagicMock()),
                patch("redis.asyncio.Redis", return_value=MagicMock()),
            ):
                await client.post("/api/v1/brief/regenerate")
        finally:
            app.dependency_overrides.pop(get_arq, None)

        assert call_order == ["invalidate", "enqueue"]
