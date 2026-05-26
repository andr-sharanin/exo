"""
ARQ worker settings.

Replaces Celery. Run with:
    python -m arq app.workers.arq_settings.WorkerSettings
"""
from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.workers.tasks.secretary_tasks import generate_plan_task
from app.workers.tasks.brief_tasks import generate_morning_brief_task
from app.workers.tasks.review_tasks import (
    create_daily_review_task,
    create_weekly_review_task,
    create_monthly_review_task,
)
from app.workers.tasks.analysis_tasks import analyze_command_task
from app.workers.tasks.cron_tasks import (
    dispatch_daily_reviews,
    dispatch_weekly_reviews,
    dispatch_monthly_reviews,
    forfeit_overdue_deposits,
    sync_ical_calendars,
)
from app.workers.tasks.stripe_tasks import charge_deposit_task


async def on_startup(ctx: dict) -> None:
    """Called once when worker process starts."""
    from app.core.database import AsyncSessionLocal
    ctx["db_factory"] = AsyncSessionLocal


async def on_shutdown(ctx: dict) -> None:
    pass


class WorkerSettings:
    functions = [
        generate_plan_task,
        generate_morning_brief_task,
        create_daily_review_task,
        create_weekly_review_task,
        create_monthly_review_task,
        analyze_command_task,
        charge_deposit_task,
    ]
    cron_jobs = [
        # Daily планёрка — 07:00 every morning (Parabellum: think once, execute all day)
        cron(dispatch_daily_reviews, hour=7, minute=0, unique=True),
        # Weekly планёрка — Friday 18:00
        cron(dispatch_weekly_reviews, weekday=4, hour=18, minute=0, unique=True),
        # Monthly планёрка — runs 09:05 daily, skips unless last day of month
        cron(dispatch_monthly_reviews, hour=9, minute=5, unique=True),
        # Stripe auto-forfeit — 09:10 daily, charges overdue deposits
        cron(forfeit_overdue_deposits, hour=9, minute=10, unique=True),
        # iCal feed sync — every 30 min, updates last_synced_at / last_error
        cron(sync_ical_calendars, minute={0, 30}, unique=True),
    ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 20
    job_timeout = 120        # seconds before job is killed
    keep_result = 3_600      # seconds to keep result in Redis
    max_tries = 3
    retry_jobs = True
