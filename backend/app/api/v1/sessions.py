import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.services.fsm import SessionStatus

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.execution_session import ExecutionSession
from app.repositories import ExecutionSessionRepo, StepObjectRepo
from app.schemas import ExecutionSessionCreate, ExecutionSessionResponse
from app.services import audit

router = APIRouter(tags=["pipeline: sessions"])


@router.post(
    "/steps/{step_id}/sessions",
    response_model=ExecutionSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    step_id: uuid.UUID,
    body: ExecutionSessionCreate,
    db: TenantDB,
    user: CurrentUser,
) -> ExecutionSession:
    await StepObjectRepo(db).get_or_404(step_id, user.tenant_id)

    # Only one active session per step at a time
    repo = ExecutionSessionRepo(db)
    active = await repo.get_active_for_step(step_id, user.tenant_id)
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step {step_id} already has an active session: {active.id}",
        )

    session = ExecutionSession(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        step_id=step_id,
        session_started_at=body.session_started_at,
        execution_mode=body.execution_mode,
        status=SessionStatus.ACTIVE,
    )
    await repo.create(session)
    await audit.record(
        db, object_type="ExecutionSession", object_id=session.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status=SessionStatus.ACTIVE,
    )
    return session


@router.get("/sessions/{session_id}", response_model=ExecutionSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> ExecutionSession:
    return await ExecutionSessionRepo(db).get_or_404(session_id, user.tenant_id)
