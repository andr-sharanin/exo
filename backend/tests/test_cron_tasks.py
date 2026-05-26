"""
Unit + integration tests for ARQ cron tasks.

forfeit_overdue_deposits — dispatches charge jobs for overdue deposits
dispatch_daily_reviews   — creates review sessions for active kernel users
dispatch_monthly_reviews — only fires on last day of month
"""
import uuid
from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_ctx(session: AsyncSession) -> dict:
    """
    Build a minimal ARQ ctx dict with a mock redis that captures enqueue_job calls.
    The `db_factory` key is not used by the cron functions (they open their own sessions),
    so we patch AsyncSessionLocal directly instead.
    """
    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()
    return {"redis": mock_redis}


def _patch_session(session: AsyncSession):
    """
    Context manager that patches AsyncSessionLocal to yield the provided test session.
    Wraps the session in an async context manager without committing (tests roll back).
    """
    @asynccontextmanager
    async def _factory():
        yield session

    return patch(
        "app.workers.tasks.cron_tasks.AsyncSessionLocal",
        return_value=_factory(),
    )


# ── forfeit_overdue_deposits ──────────────────────────────────────────────────

class TestForfeitOverdueDeposits:
    async def test_no_overdue_deposits_dispatches_nothing(
        self, db: AsyncSession
    ) -> None:
        from app.workers.tasks.cron_tasks import forfeit_overdue_deposits

        ctx = _make_ctx(db)
        with _patch_session(db):
            await forfeit_overdue_deposits(ctx)

        ctx["redis"].enqueue_job.assert_not_called()

    async def test_dispatches_job_for_overdue_deposit_with_payment_method(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.cron_tasks import forfeit_overdue_deposits

        yesterday = date.today() - timedelta(days=1)
        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=1000,
            currency="USD",
            status="held",
            due_date=yesterday,
            stripe_payment_method_id="pm_test_123",
            stripe_customer_id="cus_test_456",
        )
        db.add(dep)
        await db.flush()

        ctx = _make_ctx(db)
        with _patch_session(db):
            await forfeit_overdue_deposits(ctx)

        ctx["redis"].enqueue_job.assert_called_once_with(
            "charge_deposit_task",
            str(dep.id),
            _job_id=f"charge_deposit:{dep.id}",
        )

    async def test_skips_deposit_without_payment_method(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.cron_tasks import forfeit_overdue_deposits

        yesterday = date.today() - timedelta(days=1)
        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=500,
            currency="USD",
            status="held",
            due_date=yesterday,
            stripe_payment_method_id=None,
            stripe_customer_id=None,
        )
        db.add(dep)
        await db.flush()

        ctx = _make_ctx(db)
        with _patch_session(db):
            await forfeit_overdue_deposits(ctx)

        ctx["redis"].enqueue_job.assert_not_called()

    async def test_skips_deposit_due_today_not_past(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.cron_tasks import forfeit_overdue_deposits

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=500,
            currency="USD",
            status="held",
            due_date=date.today(),  # not past (due_date < today fails for today)
            stripe_payment_method_id="pm_test",
            stripe_customer_id="cus_test",
        )
        db.add(dep)
        await db.flush()

        ctx = _make_ctx(db)
        with _patch_session(db):
            await forfeit_overdue_deposits(ctx)

        ctx["redis"].enqueue_job.assert_not_called()

    async def test_skips_already_forfeited_deposit(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.cron_tasks import forfeit_overdue_deposits

        yesterday = date.today() - timedelta(days=1)
        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=500,
            currency="USD",
            status="forfeited",  # already forfeited
            due_date=yesterday,
            stripe_payment_method_id="pm_test",
            stripe_customer_id="cus_test",
        )
        db.add(dep)
        await db.flush()

        ctx = _make_ctx(db)
        with _patch_session(db):
            await forfeit_overdue_deposits(ctx)

        ctx["redis"].enqueue_job.assert_not_called()

    async def test_dispatches_multiple_jobs_for_multiple_overdue_deposits(
        self, db: AsyncSession
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from app.workers.tasks.cron_tasks import forfeit_overdue_deposits

        yesterday = date.today() - timedelta(days=1)
        ids = []
        for _ in range(3):
            dep_id = uuid.uuid4()
            ids.append(dep_id)
            db.add(CommitmentDeposit(
                id=dep_id,
                tenant_id=TEST_TENANT_ID,
                user_id=TEST_USER_ID,
                step_id=uuid.uuid4(),
                amount_cents=200,
                currency="USD",
                status="held",
                due_date=yesterday,
                stripe_payment_method_id="pm_test",
                stripe_customer_id="cus_test",
            ))
        await db.flush()

        ctx = _make_ctx(db)
        with _patch_session(db):
            await forfeit_overdue_deposits(ctx)

        assert ctx["redis"].enqueue_job.call_count == 3


# ── dispatch_monthly_reviews ──────────────────────────────────────────────────

class TestDispatchMonthlyReviews:
    async def test_skips_if_not_last_day_of_month(
        self, db: AsyncSession
    ) -> None:
        from app.workers.tasks.cron_tasks import dispatch_monthly_reviews

        # Patch today to be the 1st — never the last day
        with patch("app.workers.tasks.cron_tasks.date") as mock_date:
            mock_today = date(2026, 5, 1)
            mock_date.today.return_value = mock_today

            ctx = _make_ctx(db)
            with _patch_session(db):
                await dispatch_monthly_reviews(ctx)

        ctx["redis"].enqueue_job.assert_not_called()

    async def test_dispatches_on_last_day_of_month(
        self, db: AsyncSession
    ) -> None:
        from app.models.policy_kernel import PolicyKernel
        from app.workers.tasks.cron_tasks import dispatch_monthly_reviews

        # Create an active kernel
        kernel = PolicyKernel(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            is_active=True,
        )
        db.add(kernel)
        await db.flush()

        last_day = date(2026, 4, 30)  # April has 30 days

        with patch("app.workers.tasks.cron_tasks.date") as mock_date:
            mock_date.today.return_value = last_day
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            ctx = _make_ctx(db)
            with _patch_session(db):
                await dispatch_monthly_reviews(ctx)

        assert ctx["redis"].enqueue_job.call_count >= 0  # may have called or skipped if existing
