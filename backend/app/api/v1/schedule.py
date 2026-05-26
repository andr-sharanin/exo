import uuid

from fastapi import APIRouter, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.schedule_object import ScheduleObject
from app.repositories import DecisionObjectRepo, ScheduleObjectRepo
from app.schemas import ScheduleObjectCreate, ScheduleObjectResponse
from app.services import audit

router = APIRouter(tags=["pipeline: schedule"])


@router.post(
    "/decisions/{decision_id}/schedule",
    response_model=ScheduleObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    decision_id: uuid.UUID,
    body: ScheduleObjectCreate,
    db: TenantDB,
    user: CurrentUser,
) -> ScheduleObject:
    await DecisionObjectRepo(db).get_or_404(decision_id, user.tenant_id)

    repo = ScheduleObjectRepo(db)
    existing = await repo.get_by_decision(decision_id, user.tenant_id)
    if existing:
        return existing

    sched = ScheduleObject(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        decision_id=decision_id,
        schedule_mode=body.schedule_mode,
        scheduled_start=body.scheduled_start,
        scheduled_end=body.scheduled_end,
        schedule_authority_type=body.schedule_authority_type,
        status="pending",
    )
    await repo.create(sched)
    await audit.record(
        db, object_type="ScheduleObject", object_id=sched.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status="pending",
    )
    return sched


@router.get("/schedule/{schedule_id}", response_model=ScheduleObjectResponse)
async def get_schedule(
    schedule_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> ScheduleObject:
    return await ScheduleObjectRepo(db).get_or_404(schedule_id, user.tenant_id)
