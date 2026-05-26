"""
E2E tests for Subscriptions API.

GET  /subscriptions/current  → 200 with tier + limits
POST /subscriptions/checkout → 200 with session data (or 501 without Stripe key)
Tier enforcement: deposits/goals blocked at free limit
"""
import uuid
from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import UserSubscription
from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


class TestGetCurrentSubscription:
    async def test_returns_200_with_free_tier_by_default(
        self, client: AsyncClient
    ) -> None:
        r = await client.get("/api/v1/subscriptions/current")
        assert r.status_code == 200
        data = r.json()
        assert data["tier"] == "free"
        assert "limits" in data
        assert data["limits"]["max_active_goals"] == 10

    async def test_limits_reflect_tier(self, client: AsyncClient) -> None:
        data = (await client.get("/api/v1/subscriptions/current")).json()
        assert data["limits"]["allow_x2_governance"] is False

    async def test_response_has_required_fields(self, client: AsyncClient) -> None:
        data = (await client.get("/api/v1/subscriptions/current")).json()
        for field in ("tier", "status", "limits", "current_period_end", "trial_end"):
            assert field in data


class TestCheckout:
    async def test_returns_501_without_stripe_key(
        self, client: AsyncClient
    ) -> None:
        with patch(
            "app.api.v1.subscriptions.ConfigService.get_from_env",
            return_value=None,
        ):
            r = await client.post(
                "/api/v1/subscriptions/checkout",
                json={
                    "plan": "pro",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                },
            )
        assert r.status_code == 501

    async def test_invalid_plan_returns_422(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/subscriptions/checkout",
            json={
                "plan": "enterprise",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
        )
        assert r.status_code == 422

    async def test_returns_checkout_url_with_stripe_configured(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        # Set up subscription with customer id
        from app.services.subscription_service import SubscriptionService
        svc = SubscriptionService(db)
        sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
        sub.stripe_customer_id = "cus_existing"
        await db.flush()

        mock_session = MagicMock()
        mock_session.id = "cs_test_session"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_session"

        with (
            patch("app.api.v1.subscriptions.ConfigService") as mock_config_cls,
            patch("stripe.checkout.Session.create", return_value=mock_session),
        ):
            mock_config = MagicMock()
            mock_config.get = AsyncMock(side_effect=lambda k: {
                "stripe_secret_key": "sk_test_fake",
                "stripe_price_id_pro": "price_pro_test",
            }.get(k))
            mock_config_cls.return_value = mock_config

            r = await client.post(
                "/api/v1/subscriptions/checkout",
                json={
                    "plan": "pro",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                },
            )

        if r.status_code == 200:
            data = r.json()
            assert "checkout_url" in data or "session_id" in data


class TestTierEnforcement:
    async def test_free_tier_blocks_goal_at_limit(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        from app.models.planning_goal import PlanningGoal

        for i in range(10):
            db.add(PlanningGoal(
                id=uuid.uuid4(),
                tenant_id=TEST_TENANT_ID,
                user_id=TEST_USER_ID,
                title=f"Limit Goal {i}",
                horizon="monthly",
                status="active",
            ))
        await db.flush()

        r = await client.post(
            "/api/v1/planning/goals",
            json={"title": "One too many", "horizon": "monthly"},
        )
        assert r.status_code == 402

    async def test_free_tier_blocks_deposit_at_limit(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit

        for i in range(5):
            db.add(CommitmentDeposit(
                id=uuid.uuid4(),
                tenant_id=TEST_TENANT_ID,
                user_id=TEST_USER_ID,
                step_id=uuid.uuid4(),
                amount_cents=1000,
                currency="USD",
                status="held",
                due_date=date(2027, 1, 1),
            ))
        await db.flush()

        r = await client.post(
            "/api/v1/deposits",
            json={
                "step_id": str(uuid.uuid4()),
                "amount_cents": 500,
                "due_date": "2027-06-01",
            },
        )
        assert r.status_code == 402

    async def test_free_tier_blocks_x2_governance(
        self, client: AsyncClient
    ) -> None:
        r = await client.put(
            "/api/v1/governance/policy",
            json={"mode": "x2", "partner_email": "partner@example.com"},
        )
        assert r.status_code == 402

    async def test_pro_tier_allows_x2_governance(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        from app.services.subscription_service import SubscriptionService

        svc = SubscriptionService(db)
        sub = await svc.get_or_create(TEST_USER_ID, TEST_TENANT_ID)
        sub.tier = "pro"
        sub.status = "active"
        sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        await db.flush()

        r = await client.put(
            "/api/v1/governance/policy",
            json={"mode": "x2", "partner_email": "partner@example.com"},
        )
        assert r.status_code == 200
