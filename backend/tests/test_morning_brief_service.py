"""
Unit tests for MorningBriefService.

Redis is replaced with an in-memory stub; AI calls are monkeypatched.
DB queries use the shared test session.
"""
import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.morning_brief import MorningBriefService, _default_brief
from tests.conftest import TEST_USER_ID, TEST_TENANT_ID


class _FakeRedis:
    """Minimal in-memory Redis stub."""

    def __init__(self):
        self._store: dict[str, tuple[str, int]] = {}

    async def get(self, key: str):
        return self._store.get(key, (None, 0))[0]

    async def setex(self, key: str, ttl: int, value: str):
        self._store[key] = (value, ttl)

    async def delete(self, key: str):
        self._store.pop(key, None)

    def has(self, key: str) -> bool:
        return key in self._store


# ── _default_brief ────────────────────────────────────────────────────────────

def test_default_brief_structure():
    brief = _default_brief()
    assert "greeting" in brief
    assert "bullets" in brief
    assert isinstance(brief["bullets"], list)
    assert len(brief["bullets"]) >= 1
    assert "focus_recommendation" in brief
    assert "energy_tip" in brief


def test_default_brief_bullets_have_emoji_and_text():
    for bullet in _default_brief()["bullets"]:
        assert "emoji" in bullet
        assert "text" in bullet


# ── cache helpers ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_cached_returns_none_when_empty(db: AsyncSession):
    redis = _FakeRedis()
    svc = MorningBriefService(db, redis)
    result = await svc.get_cached(str(TEST_USER_ID))
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_returns_stored_brief(db: AsyncSession):
    redis = _FakeRedis()
    svc = MorningBriefService(db, redis)
    today = date.today().isoformat()
    cache_key = f"brief:{TEST_USER_ID}:{today}"
    stored = {"greeting": "Hello", "bullets": [], "date": today}
    redis._store[cache_key] = (json.dumps(stored), 21600)

    result = await svc.get_cached(str(TEST_USER_ID))
    assert result is not None
    assert result["greeting"] == "Hello"


@pytest.mark.asyncio
async def test_invalidate_removes_cache(db: AsyncSession):
    redis = _FakeRedis()
    svc = MorningBriefService(db, redis)
    today = date.today().isoformat()
    key = f"brief:{TEST_USER_ID}:{today}"
    redis._store[key] = (json.dumps({"date": today}), 100)

    await svc.invalidate(str(TEST_USER_ID))
    assert not redis.has(key)


# ── generate with mocked AI ───────────────────────────────────────────────────

_VALID_AI_RESPONSE = json.dumps({
    "greeting": "Доброе утро!",
    "bullets": [{"emoji": "🎯", "text": "Главная задача"}],
    "focus_recommendation": "Начни с приоритета.",
    "energy_tip": "Пей воду.",
})


@pytest.mark.asyncio
async def test_generate_calls_ai_and_caches(db: AsyncSession):
    redis = _FakeRedis()
    svc = MorningBriefService(db, redis)

    with patch.object(svc.ai, "complete", AsyncMock(return_value=_VALID_AI_RESPONSE)):
        brief = await svc.generate(str(TEST_USER_ID), str(TEST_TENANT_ID))

    assert brief["greeting"] == "Доброе утро!"
    assert "generated_at" in brief
    assert "date" in brief
    # Should be cached now
    cached = await svc.get_cached(str(TEST_USER_ID))
    assert cached is not None
    assert cached["greeting"] == "Доброе утро!"


@pytest.mark.asyncio
async def test_generate_falls_back_to_default_on_ai_error(db: AsyncSession):
    redis = _FakeRedis()
    svc = MorningBriefService(db, redis)

    with patch.object(svc.ai, "complete", AsyncMock(side_effect=RuntimeError("AI down"))):
        brief = await svc.generate(str(TEST_USER_ID), str(TEST_TENANT_ID))

    # Should still return a valid brief (default)
    assert "greeting" in brief
    assert "bullets" in brief
    assert "generated_at" in brief


@pytest.mark.asyncio
async def test_generate_falls_back_on_invalid_json(db: AsyncSession):
    redis = _FakeRedis()
    svc = MorningBriefService(db, redis)

    with patch.object(svc.ai, "complete", AsyncMock(return_value="not-json-at-all")):
        brief = await svc.generate(str(TEST_USER_ID), str(TEST_TENANT_ID))

    assert "greeting" in brief


# ── _build_context returns correct shape ─────────────────────────────────────

@pytest.mark.asyncio
async def test_build_context_returns_expected_keys(db: AsyncSession):
    redis = _FakeRedis()
    svc = MorningBriefService(db, redis)

    ctx = await svc._build_context(str(TEST_USER_ID))

    expected_keys = {
        "date", "energy_state", "energy_score",
        "plan_items_count", "plan_status", "plan_preview",
        "pending_confirmations", "pending_habits", "active_goals",
    }
    assert expected_keys.issubset(ctx.keys())


@pytest.mark.asyncio
async def test_build_context_defaults_when_no_data(db: AsyncSession):
    redis = _FakeRedis()
    svc = MorningBriefService(db, redis)

    ctx = await svc._build_context(str(TEST_USER_ID))

    assert ctx["energy_state"] == "unknown"
    assert ctx["energy_score"] is None
    assert ctx["plan_items_count"] == 0
    assert ctx["plan_status"] == "not_generated"
    assert ctx["pending_confirmations"] == 0
    assert ctx["pending_habits"] == []
    assert ctx["active_goals"] == []
