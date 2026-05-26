"""Background tasks: create review sessions on schedule."""


async def create_daily_review_task(ctx: dict, user_id: str, tenant_id: str) -> dict:
    """
    ARQ task: create daily планёрка session with AI agenda.
    Scheduled at 07:00 for every active user.
    After creation → publish SSE 'review_ready' event.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.review_service import ReviewService
    from app.services.event_publisher import publish

    async with AsyncSessionLocal() as db:
        try:
            svc = ReviewService(db)
            session = await svc.create_daily_session(user_id, tenant_id)
            await db.commit()
            await publish(user_id, "review_ready", {
                "session_id": str(session.id),
                "review_type": "daily",
            })
            return {"session_id": str(session.id), "status": "done"}
        except Exception as exc:
            await publish(user_id, "job_failed", {
                "job": "daily_review",
                "error": str(exc),
            })
            raise


async def create_weekly_review_task(ctx: dict, user_id: str, tenant_id: str) -> dict:
    """ARQ task: create weekly планёрка session."""
    from app.core.database import AsyncSessionLocal
    from app.services.review_service import ReviewService
    from app.services.event_publisher import publish

    async with AsyncSessionLocal() as db:
        try:
            svc = ReviewService(db)
            session = await svc.create_weekly_session(user_id, tenant_id)
            await db.commit()
            await publish(user_id, "review_ready", {
                "session_id": str(session.id),
                "review_type": "weekly",
            })
            return {"session_id": str(session.id), "status": "done"}
        except Exception as exc:
            await publish(user_id, "job_failed", {
                "job": "weekly_review",
                "error": str(exc),
            })
            raise


async def create_monthly_review_task(ctx: dict, user_id: str, tenant_id: str) -> dict:
    """ARQ task: create monthly планёрка session."""
    from app.core.database import AsyncSessionLocal
    from app.services.review_service import ReviewService
    from app.services.event_publisher import publish

    async with AsyncSessionLocal() as db:
        try:
            svc = ReviewService(db)
            session = await svc.create_monthly_session(user_id, tenant_id)
            await db.commit()
            await publish(user_id, "review_ready", {
                "session_id": str(session.id),
                "review_type": "monthly",
            })
            return {"session_id": str(session.id), "status": "done"}
        except Exception as exc:
            await publish(user_id, "job_failed", {
                "job": "monthly_review",
                "error": str(exc),
            })
            raise
