"""Background task: generate AI morning brief."""


async def generate_morning_brief_task(ctx: dict, user_id: str, tenant_id: str) -> dict:
    """
    ARQ task: build morning brief and cache in Redis (6 h TTL).
    Published to SSE channel so dashboard auto-refreshes.
    """
    import redis.asyncio as aioredis
    from app.core.config import settings
    from app.services.event_publisher import publish
    from app.services.morning_brief import MorningBriefService
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Create a dedicated short-lived Redis client for caching (not pub/sub pool)
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            svc = MorningBriefService(db, redis=r)
            brief = await svc.generate(user_id, tenant_id)
            await r.aclose()

            await publish(user_id, "brief_ready", {"bullets_count": len(brief.get("bullets", []))})
            return {"status": "done", "bullets": len(brief.get("bullets", []))}

        except Exception as exc:
            await publish(user_id, "job_failed", {"job": "morning_brief", "error": str(exc)})
            raise
