"""
ARQ cron tasks — fire on schedule, enumerate active users, dispatch review jobs.

Schedules (set in arq_settings.WorkerSettings.cron_jobs):
  daily    → 07:00 every day
  weekly   → Friday 18:00
  monthly  → 09:00 every day, skips unless today == last day of month
"""
from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

log = logging.getLogger(__name__)


async def forfeit_overdue_deposits(ctx: dict) -> None:
    """
    Daily cron: find held deposits past their due_date that have a saved
    payment method and dispatch a charge_deposit_task for each.

    Runs at 09:00 daily (registered in arq_settings).
    Only dispatches when stripe_payment_method_id is set — if no card was saved,
    the deposit is left held and the user is not silently charged.
    """
    from sqlalchemy import select, and_
    from app.core.database import AsyncSessionLocal
    from app.models.commitment_deposit import CommitmentDeposit

    today = date.today()

    async with AsyncSessionLocal() as db:
        q = select(CommitmentDeposit.id).where(
            and_(
                CommitmentDeposit.status == "held",
                CommitmentDeposit.due_date < today,
                CommitmentDeposit.stripe_payment_method_id.isnot(None),
                CommitmentDeposit.stripe_customer_id.isnot(None),
            )
        )
        overdue_ids = [str(row[0]) for row in (await db.execute(q)).all()]

    if not overdue_ids:
        log.info("forfeit_overdue_deposits: no overdue deposits with saved payment methods")
        return

    arq = ctx["redis"]
    for deposit_id in overdue_ids:
        await arq.enqueue_job(
            "charge_deposit_task",
            deposit_id,
            _job_id=f"charge_deposit:{deposit_id}",
        )

    log.info("forfeit_overdue_deposits: dispatched %d charge jobs", len(overdue_ids))


async def dispatch_daily_reviews(ctx: dict) -> None:
    """Create morning planning session for every user with an active PolicyKernel."""
    from app.core.database import AsyncSessionLocal
    from app.models.policy_kernel import PolicyKernel
    from app.models.review_session import ReviewSession
    from app.workers.tasks.review_tasks import create_daily_review_task

    today = date.today()

    async with AsyncSessionLocal() as db:
        # Get all users with active kernels
        users_q = select(
            PolicyKernel.user_id, PolicyKernel.tenant_id
        ).where(PolicyKernel.is_active == True)  # noqa: E712
        users = (await db.execute(users_q)).all()

        if not users:
            return

        # Find users who already have a session today (idempotency guard)
        day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        existing_q = select(ReviewSession.user_id).where(
            ReviewSession.review_type == "daily",
            ReviewSession.created_at >= day_start,
            ReviewSession.created_at < day_end,
        )
        already_done = {row[0] for row in (await db.execute(existing_q)).all()}

    arq = ctx["redis"]
    dispatched = 0
    for user_id, tenant_id in users:
        if user_id in already_done:
            continue
        await arq.enqueue_job(
            "create_daily_review_task",
            str(user_id),
            str(tenant_id),
            _job_id=f"daily_review:{user_id}:{today.isoformat()}",
        )
        dispatched += 1

    log.info("dispatch_daily_reviews: %d sessions queued for %s", dispatched, today)


async def dispatch_weekly_reviews(ctx: dict) -> None:
    """Create weekly review session for every user with an active PolicyKernel (Friday 18:00)."""
    from app.core.database import AsyncSessionLocal
    from app.models.policy_kernel import PolicyKernel
    from app.models.review_session import ReviewSession

    today = date.today()
    week_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) - timedelta(days=1)
    week_end = week_start + timedelta(days=2)

    async with AsyncSessionLocal() as db:
        users_q = select(
            PolicyKernel.user_id, PolicyKernel.tenant_id
        ).where(PolicyKernel.is_active == True)  # noqa: E712
        users = (await db.execute(users_q)).all()

        existing_q = select(ReviewSession.user_id).where(
            ReviewSession.review_type == "weekly",
            ReviewSession.created_at >= week_start,
            ReviewSession.created_at < week_end,
        )
        already_done = {row[0] for row in (await db.execute(existing_q)).all()}

    arq = ctx["redis"]
    dispatched = 0
    for user_id, tenant_id in users:
        if user_id in already_done:
            continue
        await arq.enqueue_job(
            "create_weekly_review_task",
            str(user_id),
            str(tenant_id),
            _job_id=f"weekly_review:{user_id}:{today.isoformat()}",
        )
        dispatched += 1

    log.info("dispatch_weekly_reviews: %d sessions queued", dispatched)


async def dispatch_monthly_reviews(ctx: dict) -> None:
    """Create monthly review session on the last day of each month (runs daily, skips early)."""
    today = date.today()
    last_day_of_month = monthrange(today.year, today.month)[1]
    if today.day != last_day_of_month:
        return

    from app.core.database import AsyncSessionLocal
    from app.models.policy_kernel import PolicyKernel
    from app.models.review_session import ReviewSession

    month_start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    month_end = datetime(today.year, today.month, last_day_of_month, 23, 59, 59, tzinfo=timezone.utc)

    async with AsyncSessionLocal() as db:
        users_q = select(
            PolicyKernel.user_id, PolicyKernel.tenant_id
        ).where(PolicyKernel.is_active == True)  # noqa: E712
        users = (await db.execute(users_q)).all()

        existing_q = select(ReviewSession.user_id).where(
            ReviewSession.review_type == "monthly",
            ReviewSession.created_at >= month_start,
            ReviewSession.created_at <= month_end,
        )
        already_done = {row[0] for row in (await db.execute(existing_q)).all()}

    arq = ctx["redis"]
    dispatched = 0
    for user_id, tenant_id in users:
        if user_id in already_done:
            continue
        await arq.enqueue_job(
            "create_monthly_review_task",
            str(user_id),
            str(tenant_id),
            _job_id=f"monthly_review:{user_id}:{today.year}-{today.month:02d}",
        )
        dispatched += 1

    log.info("dispatch_monthly_reviews: %d sessions queued for %s-%02d",
             dispatched, today.year, today.month)


async def sync_ical_calendars(ctx: dict) -> None:
    """
    Every 30 min: fetch all active iCal integrations, update last_synced_at / last_error.

    This pre-warms the data and surfaces broken feeds early.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.calendar_integration import CalendarIntegration
    from app.services.calendar_sync import ICalAdapter

    async with AsyncSessionLocal() as db:
        q = select(CalendarIntegration).where(
            CalendarIntegration.provider == "ical",
            CalendarIntegration.is_active == True,  # noqa: E712
        )
        integrations = list((await db.execute(q)).scalars().all())

        if not integrations:
            log.debug("sync_ical_calendars: no active iCal integrations")
            return

        ok = 0
        failed = 0
        now = datetime.now(timezone.utc)
        for integ in integrations:
            try:
                adapter = ICalAdapter(integ.calendar_url or "")
                await adapter.fetch_events(days_ahead=14)
                integ.last_synced_at = now
                integ.last_error = None
                ok += 1
            except Exception as exc:
                integ.last_error = str(exc)[:512]
                failed += 1
                log.warning("sync_ical_calendars: integration %s failed: %s", integ.id, exc)

        await db.flush()
        await db.commit()

    log.info("sync_ical_calendars: %d ok, %d failed", ok, failed)
