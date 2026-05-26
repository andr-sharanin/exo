import uuid

from fastapi import APIRouter, Query, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.step_object import StepObject
from app.repositories import DecisionObjectRepo, StepObjectRepo
from app.schemas import StepObjectCreate, StepObjectResponse
from app.services import audit

router = APIRouter(tags=["pipeline: steps"])


@router.post(
    "/decisions/{decision_id}/steps",
    response_model=StepObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_step(
    decision_id: uuid.UUID,
    body: StepObjectCreate,
    db: TenantDB,
    user: CurrentUser,
) -> StepObject:
    await DecisionObjectRepo(db).get_or_404(decision_id, user.tenant_id)

    step = StepObject(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        decision_id=decision_id,
        step_type=body.step_type,
        execution_readiness=body.execution_readiness,
        title=body.title,
        definition_of_done_ref=body.definition_of_done_ref,
        step_order=body.step_order,
        estimated_minutes=body.estimated_minutes,
        status="pending",
    )
    repo = StepObjectRepo(db)
    await repo.create(step)
    await audit.record(
        db, object_type="StepObject", object_id=step.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status="pending",
    )
    return step


@router.get("/steps", response_model=list[StepObjectResponse])
async def list_user_steps(db: TenantDB, user: CurrentUser) -> list[StepObject]:
    """Return all active (non-terminal) steps for the current user."""
    return await StepObjectRepo(db).list_active_for_user(user.tenant_id, user.user_id)


@router.get("/steps/quick-queue", response_model=list[StepObjectResponse])
async def list_quick_wins(
    db: TenantDB,
    user: CurrentUser,
    max_minutes: int = Query(15, ge=1, le=60),
) -> list[StepObject]:
    """Return ready steps with estimated_minutes <= max_minutes (default 15)."""
    return await StepObjectRepo(db).list_quick_wins(
        user.tenant_id, user.user_id, max_minutes
    )


@router.get("/steps/{step_id}", response_model=StepObjectResponse)
async def get_step(
    step_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> StepObject:
    return await StepObjectRepo(db).get_or_404(step_id, user.tenant_id)


@router.get("/decisions/{decision_id}/steps", response_model=list[StepObjectResponse])
async def list_steps_for_decision(
    decision_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> list[StepObject]:
    await DecisionObjectRepo(db).get_or_404(decision_id, user.tenant_id)
    return await StepObjectRepo(db).list_by_decision(decision_id, user.tenant_id)
