"""
Phase 8 — Planning Goals API

POST   /planning/goals             — create goal at a horizon
GET    /planning/goals             — list goals (optional ?horizon= filter)
POST   /planning/goals/{id}/complete — mark completed (409 if not active)
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.planning_goal import PlanningGoal
from app.repositories.planning_repos import PlanningGoalRepo
from app.schemas.planning_schemas import PlanningGoalCreate, PlanningGoalResponse
from app.services.planning import PlanningGoalService

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/goals", response_model=PlanningGoalResponse, status_code=201)
async def create_goal(
    body: PlanningGoalCreate, db: TenantDB, user: CurrentUser
) -> PlanningGoalResponse:
    from app.services.subscription_service import SubscriptionService
    await SubscriptionService(db).assert_can_create_goal(user.user_id, user.tenant_id)

    repo = PlanningGoalRepo(db)

    # Validate parent hierarchy
    if body.parent_id is not None:
        parent_horizon = await repo.get_parent_horizon(body.parent_id, user.tenant_id)
        if parent_horizon is None:
            raise HTTPException(status_code=404, detail="Parent goal not found")
        if not PlanningGoalService.is_valid_parent(parent_horizon, body.horizon):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Goal at horizon '{body.horizon}' cannot be child of "
                    f"'{parent_horizon}' — child must be a lower horizon"
                ),
            )

    goal = await repo.create(
        PlanningGoal(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            horizon=body.horizon,
            title=body.title,
            description=body.description,
            status="active",
            parent_id=body.parent_id,
            target_date=body.target_date,
        )
    )
    return PlanningGoalResponse.model_validate(goal)


@router.get("/goals", response_model=list[PlanningGoalResponse])
async def list_goals(
    db: TenantDB,
    user: CurrentUser,
    horizon: Optional[str] = Query(None),
) -> list[PlanningGoalResponse]:
    repo = PlanningGoalRepo(db)
    if horizon is not None:
        if horizon not in PlanningGoalService.HORIZON_ORDER:
            raise HTTPException(status_code=422, detail=f"Unknown horizon: {horizon}")
        goals = await repo.list_by_horizon(user.tenant_id, horizon)
    else:
        goals = await repo.list_by_tenant(user.tenant_id)
    return [PlanningGoalResponse.model_validate(g) for g in goals]


@router.post("/goals/{goal_id}/complete", response_model=PlanningGoalResponse)
async def complete_goal(
    goal_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> PlanningGoalResponse:
    repo = PlanningGoalRepo(db)
    goal = await repo.get_or_404(goal_id, user.tenant_id)
    if goal.status != "active":
        raise HTTPException(status_code=409, detail="Goal is not in active status")
    goal.status = "completed"
    goal.completed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(goal)
    return PlanningGoalResponse.model_validate(goal)
