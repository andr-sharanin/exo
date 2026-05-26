"""
Generic FSM transition endpoint.
One endpoint handles all canonical object status mutations.
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models import (
    Command, CaptureRecord, ReasoningArtifact, DecisionObject,
    ScheduleObject, StepObject, ExecutionSession, WitnessObject,
    EntitySession, MemoryObject, BehavioralEvent,
)
from app.schemas.common import TransitionRequest, TransitionResponse
from app.services import audit
from app.services.fsm import fsm, IllegalTransitionError

router = APIRouter(tags=["pipeline: transitions"])

# URL slug → (SQLAlchemy model, FSM object_type name)
_REGISTRY: dict[str, tuple[type, str]] = {
    "commands":            (Command,            "Command"),
    "capture-records":     (CaptureRecord,      "CaptureRecord"),
    "reasoning-artifacts": (ReasoningArtifact,  "ReasoningArtifact"),
    "decisions":           (DecisionObject,     "DecisionObject"),
    "schedules":           (ScheduleObject,     "ScheduleObject"),
    "steps":               (StepObject,         "StepObject"),
    "sessions":            (ExecutionSession,   "ExecutionSession"),
    "witnesses":           (WitnessObject,      "WitnessObject"),
    "entity-sessions":     (EntitySession,      "EntitySession"),
    "memory":              (MemoryObject,       "MemoryObject"),
    "behavioral-events":   (BehavioralEvent,    "BehavioralEvent"),
}


@router.post(
    "/transition/{object_slug}/{object_id}",
    response_model=TransitionResponse,
)
async def transition_object(
    object_slug: str,
    object_id: uuid.UUID,
    body: TransitionRequest,
    db: TenantDB,
    user: CurrentUser,
) -> TransitionResponse:
    entry = _REGISTRY.get(object_slug)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown object type: '{object_slug}'",
        )

    model_cls, fsm_type = entry
    result = await db.execute(
        select(model_cls).where(
            model_cls.id == object_id,
            model_cls.tenant_id == user.tenant_id,
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{fsm_type} {object_id} not found",
        )

    prev_status: str = obj.status
    try:
        new_status = fsm.transition(fsm_type, prev_status, body.action)
    except IllegalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    obj.status = new_status
    await audit.record(
        db,
        object_type=fsm_type,
        object_id=obj.id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        action=body.action,
        from_status=prev_status,
        to_status=new_status,
        metadata=body.metadata,
    )

    return TransitionResponse(
        id=obj.id,
        object_type=fsm_type,
        previous_status=prev_status,
        current_status=new_status,
        allowed_next_actions=fsm.allowed_actions(fsm_type, new_status),
    )
