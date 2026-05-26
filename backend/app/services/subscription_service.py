"""
SubscriptionService — tier management and quota enforcement.

Tier limits:
  free:
    - max 10 active planning goals
    - max 5 held commitment deposits
    - governance mode: solo only (x2 disallowed)
    - max 1 active calendar integration
    - all 7 system modes available (modes are free, energy management is a core feature)

  pro:
    - unlimited goals, deposits, calendar integrations
    - x2 governance mode
    - all features

  team:
    - all pro features
    - multiple users per tenant
    - (tenant admin manages members — enforced via separate middleware, not here)

Usage:
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(user_id, tenant_id)
    await svc.assert_can_create_goal(user_id, tenant_id)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import UserSubscription

# ── Limits ────────────────────────────────────────────────────────────────────

TIER_LIMITS: dict[str, dict] = {
    "free": {
        "max_active_goals": 10,
        "max_held_deposits": 5,
        "allow_x2_governance": False,
        "max_calendar_integrations": 1,
    },
    "pro": {
        "max_active_goals": None,      # unlimited
        "max_held_deposits": None,
        "allow_x2_governance": True,
        "max_calendar_integrations": None,
    },
    "team": {
        "max_active_goals": None,
        "max_held_deposits": None,
        "allow_x2_governance": True,
        "max_calendar_integrations": None,
    },
}

_UPGRADE_MESSAGE = (
    "This feature requires a Pro subscription. "
    "Upgrade at /settings/subscription."
)


class SubscriptionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Core helpers ──────────────────────────────────────────────────────────

    async def get_or_create(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> UserSubscription:
        """Return subscription for user, creating a free-tier record if none exists."""
        result = await self._db.execute(
            select(UserSubscription).where(UserSubscription.user_id == user_id)
        )
        sub = result.scalar_one_or_none()
        if sub is None:
            sub = UserSubscription(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                tier="free",
                status="free",
            )
            self._db.add(sub)
            await self._db.flush()
        return sub

    async def get_tier(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        sub = await self.get_or_create(user_id, tenant_id)
        # Treat expired subscriptions as free
        if sub.tier != "free" and sub.current_period_end:
            if sub.current_period_end < datetime.now(timezone.utc):
                return "free"
        return sub.tier

    def limits(self, tier: str) -> dict:
        return TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    # ── Assertion helpers ─────────────────────────────────────────────────────

    async def assert_can_create_goal(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        from app.models.planning_goal import PlanningGoal

        tier = await self.get_tier(user_id, tenant_id)
        limit = self.limits(tier)["max_active_goals"]
        if limit is None:
            return

        count = await self._count(
            PlanningGoal,
            PlanningGoal.user_id == user_id,
            PlanningGoal.tenant_id == tenant_id,
            PlanningGoal.status == "active",
        )
        if count >= limit:
            raise HTTPException(
                402,
                f"Free tier allows up to {limit} active goals. {_UPGRADE_MESSAGE}",
            )

    async def assert_can_create_deposit(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit

        tier = await self.get_tier(user_id, tenant_id)
        limit = self.limits(tier)["max_held_deposits"]
        if limit is None:
            return

        count = await self._count(
            CommitmentDeposit,
            CommitmentDeposit.user_id == user_id,
            CommitmentDeposit.tenant_id == tenant_id,
            CommitmentDeposit.status == "held",
        )
        if count >= limit:
            raise HTTPException(
                402,
                f"Free tier allows up to {limit} held deposits. {_UPGRADE_MESSAGE}",
            )

    async def assert_can_use_x2_governance(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        tier = await self.get_tier(user_id, tenant_id)
        if not self.limits(tier)["allow_x2_governance"]:
            raise HTTPException(
                402,
                f"x2 governance mode requires a Pro subscription. {_UPGRADE_MESSAGE}",
            )

    async def assert_can_add_calendar(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        from app.models.calendar_integration import CalendarIntegration

        tier = await self.get_tier(user_id, tenant_id)
        limit = self.limits(tier)["max_calendar_integrations"]
        if limit is None:
            return

        count = await self._count(
            CalendarIntegration,
            CalendarIntegration.user_id == user_id,
            CalendarIntegration.tenant_id == tenant_id,
            CalendarIntegration.is_active == True,  # noqa: E712
        )
        if count >= limit:
            raise HTTPException(
                402,
                f"Free tier allows {limit} calendar integration. {_UPGRADE_MESSAGE}",
            )

    # ── Stripe lifecycle ──────────────────────────────────────────────────────

    async def apply_stripe_event(
        self,
        event_type: str,
        subscription_obj: dict,
    ) -> None:
        """Update UserSubscription from a Stripe customer.subscription.* event."""
        stripe_sub_id = subscription_obj.get("id", "")
        stripe_customer_id = subscription_obj.get("customer", "")
        stripe_price_id = (
            (subscription_obj.get("items", {}).get("data") or [{}])[0]
            .get("price", {})
            .get("id", "")
        )
        status = subscription_obj.get("status", "active")
        period_end_ts = subscription_obj.get("current_period_end")
        trial_end_ts = subscription_obj.get("trial_end")
        canceled_at_ts = subscription_obj.get("canceled_at")

        # Resolve tier from price id via config
        tier = await self._tier_from_price_id(stripe_price_id)

        # Find or create UserSubscription by stripe_subscription_id
        result = await self._db.execute(
            select(UserSubscription).where(
                UserSubscription.stripe_subscription_id == stripe_sub_id
            )
        )
        sub = result.scalar_one_or_none()

        if sub is None:
            # New subscription — try to find by customer_id
            result2 = await self._db.execute(
                select(UserSubscription).where(
                    UserSubscription.stripe_customer_id == stripe_customer_id
                )
            )
            sub = result2.scalar_one_or_none()

        if sub is None:
            # Cannot link to a user — log and skip
            import logging
            logging.getLogger(__name__).warning(
                "apply_stripe_event: cannot find UserSubscription for customer %s sub %s",
                stripe_customer_id,
                stripe_sub_id,
            )
            return

        sub.stripe_subscription_id = stripe_sub_id
        sub.stripe_customer_id = stripe_customer_id
        sub.stripe_price_id = stripe_price_id
        sub.status = status
        sub.tier = tier if status in ("active", "trialing") else "free"
        sub.updated_at = datetime.now(timezone.utc)

        if period_end_ts:
            sub.current_period_end = datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
        if trial_end_ts:
            sub.trial_end = datetime.fromtimestamp(trial_end_ts, tz=timezone.utc)
        if canceled_at_ts:
            sub.canceled_at = datetime.fromtimestamp(canceled_at_ts, tz=timezone.utc)

        if event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
            sub.tier = "free"
            sub.status = "canceled"

        await self._db.flush()

    async def _tier_from_price_id(self, price_id: str) -> str:
        """Map Stripe price_id to tier string using admin-configured price IDs."""
        if not price_id:
            return "pro"  # default if mapping not set up yet
        from app.services.config_service import ConfigService
        svc = ConfigService(self._db)
        pro_price = await svc.get("stripe_price_id_pro") or ""
        team_price = await svc.get("stripe_price_id_team") or ""
        if price_id == team_price:
            return "team"
        if price_id == pro_price:
            return "pro"
        return "pro"  # unknown price → assume pro

    # ── Private ───────────────────────────────────────────────────────────────

    async def _count(self, model, *filters) -> int:
        result = await self._db.execute(
            select(func.count()).select_from(model).where(*filters)
        )
        return result.scalar_one()
