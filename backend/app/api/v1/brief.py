"""
Morning Brief API

GET  /brief/today          — return cached brief or enqueue generation (202)
POST /brief/regenerate     — force regeneration (invalidates cache, enqueues)
"""
from arq import ArqRedis
from fastapi import APIRouter, Depends

from app.api.v1.secretary import get_arq
from app.api.v1.sse import get_redis_pool
from app.core.auth import CurrentUser
from app.core.rls import TenantDB

router = APIRouter(prefix="/brief", tags=["brief"])


@router.get("/today")
async def get_today_brief(
    db: TenantDB,
    user: CurrentUser,
    arq: ArqRedis = Depends(get_arq),
) -> dict:
    """
    Returns today's morning brief.

    If brief is cached in Redis → return it (200).
    If not yet generated → enqueue background generation and return 202 with job_id.
    Listen for SSE event 'brief_ready' to know when it's done.
    """
    import redis.asyncio as aioredis
    from app.services.morning_brief import MorningBriefService
    from datetime import date
    from fastapi.responses import JSONResponse

    r = aioredis.Redis(connection_pool=get_redis_pool(), decode_responses=True)
    svc = MorningBriefService(db, redis=r)

    cached = await svc.get_cached(str(user.user_id))
    if cached:
        return cached

    # Not cached — enqueue generation
    today = date.today().isoformat()
    job_id = f"brief:{user.user_id}:{today}"
    job = await arq.enqueue_job(
        "generate_morning_brief_task",
        str(user.user_id),
        str(user.tenant_id),
        _job_id=job_id,
    )
    return JSONResponse(
        status_code=202,
        content={
            "status": "generating",
            "job_id": job_id,
            "queued": job is not None,
            "message": "Brief is being generated. Listen for SSE 'brief_ready' event.",
        },
    )


@router.post("/regenerate", status_code=202)
async def regenerate_brief(
    db: TenantDB,
    user: CurrentUser,
    arq: ArqRedis = Depends(get_arq),
) -> dict:
    """Force-invalidate cache and regenerate today's brief."""
    import uuid
    import redis.asyncio as aioredis
    from app.services.morning_brief import MorningBriefService

    r = aioredis.Redis(connection_pool=get_redis_pool(), decode_responses=True)
    await MorningBriefService(db, redis=r).invalidate(str(user.user_id))

    job_id = f"brief_regen:{user.user_id}:{uuid.uuid4()}"
    await arq.enqueue_job(
        "generate_morning_brief_task",
        str(user.user_id),
        str(user.tenant_id),
        _job_id=job_id,
    )
    return {"status": "queued", "job_id": job_id}
