"""
Tests for ARQ Stripe tasks.

charge_deposit_task — fetches deposit, calls StripeService, stores payment_intent_id
"""
import uuid
from contextlib import asynccontextmanager
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch_db_session(session: AsyncSession):
    """Patch AsyncSessionLocal to yield the provided test session (no-op commit)."""
    original_commit = session.commit

    @asynccontextmanager
    async def _factory():
        # Replace commit with flush so test isolation is preserved
        session.commit = session.flush  # type: ignore[assignment]
        try:
            yield session
        finally:
            session.commit = original_commit  # type: ignore[assignment]

    return patch(
        "app.workers.tasks.stripe_tasks.AsyncSessionLocal",
        return_value=_factory(),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestChargeDepositTask:
    async def test_charges_deposit_with_saved_payment_method(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.stripe_tasks import charge_deposit_task

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=5000,
            currency="USD",
            status="held",
            due_date=date.today() - timedelta(days=1),
            stripe_payment_method_id="pm_test_abc",
            stripe_customer_id="cus_test_xyz",
        )
        db.add(dep)
        await db.flush()

        ctx = {}
        with (
            _patch_db_session(db),
            patch(
                "app.workers.tasks.stripe_tasks.ConfigService"
            ) as mock_cfg_cls,
            patch(
                "app.workers.tasks.stripe_tasks.StripeService"
            ) as mock_svc_cls,
        ):
            mock_cfg = MagicMock()
            mock_cfg.get = AsyncMock(side_effect=lambda k: {
                "stripe_secret_key": "sk_test_fake",
                "stripe_charity_account": None,
            }.get(k))
            mock_cfg_cls.return_value = mock_cfg
            mock_cfg_cls.get_from_env = MagicMock(return_value=None)

            mock_svc = MagicMock()
            mock_svc.create_payment_intent = AsyncMock(return_value="pi_test_new")
            mock_svc_cls.return_value = mock_svc

            await charge_deposit_task(ctx, str(dep.id))

        # Verify payment intent was created with correct args
        mock_svc.create_payment_intent.assert_awaited_once_with(
            customer_id="cus_test_xyz",
            payment_method_id="pm_test_abc",
            amount_cents=5000,
            currency="USD",
            deposit_id=str(dep.id),
            charity_account=None,
        )

        # Deposit should have payment_intent_id set
        await db.refresh(dep)
        assert dep.stripe_payment_intent_id == "pi_test_new"

    async def test_skips_invalid_deposit_id(self, db: AsyncSession) -> None:
        from app.workers.tasks.stripe_tasks import charge_deposit_task

        ctx = {}
        with _patch_db_session(db):
            # Should not raise — just logs an error
            await charge_deposit_task(ctx, "not-a-uuid")

    async def test_skips_missing_deposit(self, db: AsyncSession) -> None:
        from app.workers.tasks.stripe_tasks import charge_deposit_task

        ctx = {}
        nonexistent = str(uuid.uuid4())
        with (
            _patch_db_session(db),
            patch("app.workers.tasks.stripe_tasks.StripeService") as mock_svc_cls,
        ):
            await charge_deposit_task(ctx, nonexistent)
            mock_svc_cls.assert_not_called()

    async def test_skips_deposit_without_payment_method(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.stripe_tasks import charge_deposit_task

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=1000,
            currency="USD",
            status="held",
            due_date=date.today() - timedelta(days=1),
            stripe_payment_method_id=None,
            stripe_customer_id=None,
        )
        db.add(dep)
        await db.flush()

        ctx = {}
        with (
            _patch_db_session(db),
            patch("app.workers.tasks.stripe_tasks.StripeService") as mock_svc_cls,
        ):
            await charge_deposit_task(ctx, str(dep.id))
            mock_svc_cls.assert_not_called()

    async def test_skips_deposit_already_forfeited(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.stripe_tasks import charge_deposit_task

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=1000,
            currency="USD",
            status="forfeited",
            due_date=date.today() - timedelta(days=1),
            stripe_payment_method_id="pm_test",
            stripe_customer_id="cus_test",
        )
        db.add(dep)
        await db.flush()

        ctx = {}
        with (
            _patch_db_session(db),
            patch("app.workers.tasks.stripe_tasks.StripeService") as mock_svc_cls,
        ):
            await charge_deposit_task(ctx, str(dep.id))
            mock_svc_cls.assert_not_called()

    async def test_handles_stripe_error_gracefully(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.stripe_tasks import charge_deposit_task

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=1000,
            currency="USD",
            status="held",
            due_date=date.today() - timedelta(days=1),
            stripe_payment_method_id="pm_test",
            stripe_customer_id="cus_test",
        )
        db.add(dep)
        await db.flush()

        ctx = {}
        with (
            _patch_db_session(db),
            patch("app.workers.tasks.stripe_tasks.ConfigService") as mock_cfg_cls,
            patch("app.workers.tasks.stripe_tasks.StripeService") as mock_svc_cls,
        ):
            mock_cfg = MagicMock()
            mock_cfg.get = AsyncMock(return_value="sk_test_fake")
            mock_cfg_cls.return_value = mock_cfg
            mock_cfg_cls.get_from_env = MagicMock(return_value=None)

            mock_svc = MagicMock()
            mock_svc.create_payment_intent = AsyncMock(
                side_effect=Exception("Card declined")
            )
            mock_svc_cls.return_value = mock_svc

            # Should not raise — Stripe errors are caught and logged
            await charge_deposit_task(ctx, str(dep.id))

        # Deposit should remain unchanged
        await db.refresh(dep)
        assert dep.stripe_payment_intent_id is None

    async def test_skips_when_no_stripe_key_configured(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.stripe_tasks import charge_deposit_task

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=1000,
            currency="USD",
            status="held",
            due_date=date.today() - timedelta(days=1),
            stripe_payment_method_id="pm_test",
            stripe_customer_id="cus_test",
        )
        db.add(dep)
        await db.flush()

        ctx = {}
        with (
            _patch_db_session(db),
            patch("app.workers.tasks.stripe_tasks.ConfigService") as mock_cfg_cls,
            patch("app.workers.tasks.stripe_tasks.StripeService") as mock_svc_cls,
        ):
            mock_cfg = MagicMock()
            mock_cfg.get = AsyncMock(return_value=None)  # no key in DB
            mock_cfg_cls.return_value = mock_cfg
            mock_cfg_cls.get_from_env = MagicMock(return_value=None)  # no key in env

            await charge_deposit_task(ctx, str(dep.id))
            mock_svc_cls.assert_not_called()
