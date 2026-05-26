"""
Phase 7 — Secretary API

POST   /secretary/plan                  — enqueue async plan generation (202)
GET    /secretary/plan/status/{job_id}  — poll ARQ job status
GET    /secretary/plan/today            — today's plan (404 if none)
POST   /secretary/plan/{id}/accept      — accept draft plan (409 if already accepted)
"""
import uuid
from datetime import datetime, timezone

from arq import ArqRedis
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import CurrentUser
from app.core.config import settings
from app.core.rls import TenantDB
from app.repositories.secretary_repos import DayPlanRepo
from app.schemas.secretary_schemas import DayPlanResponse

router = APIRouter(prefix="/secretary", tags=["secretary"])

# ── Shared ARQ pool ───────────────────────────────────────────────────────────
_arq_pool: ArqRedis | None = None


async def get_arq() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        from arq import create_pool
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/plan", status_code=202)
async def enqueue_plan(
    user: CurrentUser,
    arq: ArqRedis = Depends(get_arq),
    regenerate: bool = Query(False),
) -> dict:
    """
    Enqueue async plan generation. Returns job_id immediately.
    Listen for SSE event 'plan_ready' or poll GET /plan/status/{job_id}.

    regenerate=true forces a new job even if one ran today.
    """
    job_id = (
        str(uuid.uuid4())
        if regenerate
        else f"plan:{user.user_id}:{_today()}"
    )
    job = await arq.enqueue_job(
        "generate_plan_task",
        str(user.tenant_id),
        str(user.user_id),
        _job_id=job_id,
    )
    # arq returns None when a job with the same _job_id is already queued/running
    status = "queued" if job is not None else "already_running"
    return {"job_id": job_id, "status": status}


@router.get("/plan/status/{job_id}")
async def plan_job_status(
    job_id: str,
    arq: ArqRedis = Depends(get_arq),
) -> dict:
    """Poll ARQ job result. Use SSE 'plan_ready' event to avoid polling."""
    from arq.jobs import Job, JobStatus
    job = Job(job_id, arq)
    status = await job.status()
    if status == JobStatus.not_found:
        raise HTTPException(status_code=404, detail="Job not found")
    result = None
    if status == JobStatus.complete:
        info = await job.result_info()
        result = info.result if info else None
    return {"job_id": job_id, "status": status.value, "result": result}


@router.get("/plan/today", response_model=DayPlanResponse)
async def get_today_plan(db: TenantDB, user: CurrentUser) -> DayPlanResponse:
    plan = await DayPlanRepo(db).get_today_for_tenant(user.tenant_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan for today")
    return DayPlanResponse.model_validate(plan)


@router.post("/plan/{plan_id}/accept", response_model=DayPlanResponse)
async def accept_plan(
    plan_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> DayPlanResponse:
    repo = DayPlanRepo(db)
    plan = await repo.get_or_404(plan_id, user.tenant_id)
    if plan.status != "draft":
        raise HTTPException(status_code=409, detail="Plan is not in draft status")
    plan.status = "accepted"
    plan.accepted_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(plan)
    return DayPlanResponse.model_validate(plan)


def _today() -> str:
    from datetime import date
    return date.today().isoformat()
