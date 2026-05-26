"""
Unit tests for SubscriptionService — tier enforcement and Stripe event handling.
"""
import uuid
from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import UserSubscription
from app.services.subscription_service import SubscriptionService, TIER_LIMITS
from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


# ── TIER_LIMITS sanity ────────────────────────────────────────────────────────

def test_free_tier_has_all_limits():
    limits = TIER_LIMITS["free"]
    assert limits["max_active_goals"] == 10
    assert limits["max_held_deposits"] == 5
    assert limits["allow_x2_governance"] is False
    assert limits["max_calendar_integrations"] == 1


def test_pro_tier_is_unlimited():
    limits = TIER_LIMITS["pro"]
    assert limits["max_active_goals"] is None
    assert limits["max_held_deposits"] is None
    assert limits["allow_x2_governance"] is True
    assert limits["max_calendar_integrations"] is None


def test_team_tier_matches_pro():
    for key in ("max_active_goals", "max_held_deposits", "allow_x2_governance"):
        assert TIER_LIMITS["team"][key] == TIER_LIMITS["pro"][key]


# ── get_or_create ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_or_create_creates_free_subscription(db: AsyncSession):
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    assert sub.tier == "free"
    assert sub.status == "free"
    assert sub.user_id == TEST_USER_ID


@pytest.mark.asyncio
async def test_get_or_create_is_idempotent(db: AsyncSession):
    svc = SubscriptionService(db)
    sub1 = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    sub2 = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    assert sub1.id == sub2.id


# ── get_tier with expiry ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_tier_returns_free_when_subscription_expired(db: AsyncSession):
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    sub.tier = "pro"
    sub.status = "active"
    # Period ended yesterday
    sub.current_period_end = datetime.now(timezone.utc) - timedelta(days=1)
    await db.flush()

    tier = await svc.get_tier(TEST_USER_ID, TEST_TENANT_ID)
    assert tier == "free"


@pytest.mark.asyncio
async def test_get_tier_returns_pro_when_active(db: AsyncSession):
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    sub.tier = "pro"
    sub.status = "active"
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    await db.flush()

    tier = await svc.get_tier(TEST_USER_ID, TEST_TENANT_ID)
    assert tier == "pro"


# ── assert_can_create_goal ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_tier_allows_goal_under_limit(db: AsyncSession):
    svc = SubscriptionService(db)
    # No goals exist → count is 0, limit is 10 → should pass
    await svc.assert_can_create_goal(TEST_USER_ID, TEST_TENANT_ID)


@pytest.mark.asyncio
async def test_free_tier_blocks_goal_at_limit(db: AsyncSession):
    from fastapi import HTTPException
    from app.models.planning_goal import PlanningGoal

    # Create 10 active goals to hit the free limit
    for i in range(10):
        goal = PlanningGoal(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            title=f"Goal {i}",
            horizon="monthly",
            status="active",
        )
        db.add(goal)
    await db.flush()

    svc = SubscriptionService(db)
    with pytest.raises(HTTPException) as exc_info:
        await svc.assert_can_create_goal(TEST_USER_ID, TEST_TENANT_ID)

    assert exc_info.value.status_code == 402


@pytest.mark.asyncio
async def test_pro_tier_allows_unlimited_goals(db: AsyncSession):
    from app.models.planning_goal import PlanningGoal

    # Create 15 active goals (beyond free limit)
    for i in range(15):
        goal = PlanningGoal(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            title=f"Pro Goal {i}",
            horizon="monthly",
            status="active",
        )
        db.add(goal)
    await db.flush()

    # Set pro subscription
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    sub.tier = "pro"
    sub.status = "active"
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    await db.flush()

    # Should not raise
    await svc.assert_can_create_goal(TEST_USER_ID, TEST_TENANT_ID)


# ── assert_can_use_x2_governance ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_tier_blocks_x2_governance(db: AsyncSession):
    from fastapi import HTTPException

    svc = SubscriptionService(db)
    with pytest.raises(HTTPException) as exc_info:
        await svc.assert_can_use_x2_governance(TEST_USER_ID, TEST_TENANT_ID)

    assert exc_info.value.status_code == 402


@pytest.mark.asyncio
async def test_pro_tier_allows_x2_governance(db: AsyncSession):
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    sub.tier = "pro"
    sub.status = "active"
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    await db.flush()

    # Should not raise
    await svc.assert_can_use_x2_governance(TEST_USER_ID, TEST_TENANT_ID)


# ── apply_stripe_event ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_stripe_event_created_sets_pro_tier(db: AsyncSession):
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    sub.stripe_customer_id = "cus_test_stripe"
    await db.flush()

    now_ts = int(datetime.now(timezone.utc).timestamp())
    period_end_ts = now_ts + 30 * 86400

    with patch.object(svc, "_tier_from_price_id", AsyncMock(return_value="pro")):
        await svc.apply_stripe_event(
            "customer.subscription.created",
            {
                "id": "sub_abc123",
                "customer": "cus_test_stripe",
                "status": "active",
                "current_period_end": period_end_ts,
                "trial_end": None,
                "canceled_at": None,
                "items": {"data": [{"price": {"id": "price_pro_123"}}]},
            },
        )

    await db.refresh(sub)
    assert sub.tier == "pro"
    assert sub.status == "active"
    assert sub.stripe_subscription_id == "sub_abc123"
    assert sub.current_period_end is not None


@pytest.mark.asyncio
async def test_apply_stripe_event_deleted_downgrades_to_free(db: AsyncSession):
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
    sub.tier = "pro"
    sub.status = "active"
    sub.stripe_customer_id = "cus_will_cancel"
    sub.stripe_subscription_id = "sub_will_cancel"
    await db.flush()

    with patch.object(svc, "_tier_from_price_id", AsyncMock(return_value="pro")):
        await svc.apply_stripe_event(
            "customer.subscription.deleted",
            {
                "id": "sub_will_cancel",
                "customer": "cus_will_cancel",
                "status": "canceled",
                "current_period_end": None,
                "trial_end": None,
                "canceled_at": int(datetime.now(timezone.utc).timestamp()),
                "items": {"data": []},
            },
        )

    await db.refresh(sub)
    assert sub.tier == "free"
    assert sub.status == "canceled"
    assert sub.canceled_at is not None
