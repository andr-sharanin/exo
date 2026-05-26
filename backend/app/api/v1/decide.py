import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.decision_object import DecisionObject
from app.repositories import CaptureRecordRepo, DecisionObjectRepo
from app.schemas import DecisionObjectCreate, DecisionObjectResponse
from app.services import audit

router = APIRouter(tags=["pipeline: decide"])


@router.post(
    "/capture/{capture_id}/decide",
    response_model=DecisionObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_decision(
    capture_id: uuid.UUID,
    body: DecisionObjectCreate,
    db: TenantDB,
    user: CurrentUser,
) -> DecisionObject:
    await CaptureRecordRepo(db).get_or_404(capture_id, user.tenant_id)

    # fast_track requires fast_track_record
    if body.decision_outcome == "fast_track" and body.fast_track_record is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fast_track_record required when decision_outcome=fast_track",
        )

    repo = DecisionObjectRepo(db)
    existing = await repo.get_by_capture(capture_id, user.tenant_id)
    if existing:
        return existing

    decision = DecisionObject(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        capture_id=capture_id,
        reasoning_ref=body.reasoning_ref,
        decision_outcome=body.decision_outcome,
        confirmed_by_user=body.confirmed_by_user,
        decision_timestamp=datetime.now(timezone.utc) if body.confirmed_by_user else None,
        fast_track_record=body.fast_track_record.model_dump() if body.fast_track_record else None,
        status="pending",
    )
    await repo.create(decision)
    await audit.record(
        db, object_type="DecisionObject", object_id=decision.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status="pending",
    )
    return decision


@router.get("/decisions/{decision_id}", response_model=DecisionObjectResponse)
async def get_decision(
    decision_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> DecisionObject:
    return await DecisionObjectRepo(db).get_or_404(decision_id, user.tenant_id)
