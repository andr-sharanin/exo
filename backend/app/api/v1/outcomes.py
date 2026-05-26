import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.outcome_object import OutcomeObject
from app.repositories import OutcomeObjectRepo, StepObjectRepo, WitnessObjectRepo
from app.schemas import OutcomeObjectCreate, OutcomeObjectResponse
from app.services import audit

router = APIRouter(tags=["pipeline: outcomes"])

# outcome_type=completed requires verified witness — KDC §8 constraint
_REQUIRES_VERIFIED = {"completed"}


@router.post(
    "/steps/{step_id}/outcome",
    response_model=OutcomeObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_outcome(
    step_id: uuid.UUID,
    body: OutcomeObjectCreate,
    db: TenantDB,
    user: CurrentUser,
) -> OutcomeObject:
    await StepObjectRepo(db).get_or_404(step_id, user.tenant_id)

    # Validate witness exists and belongs to this step
    witness = await WitnessObjectRepo(db).get_or_404(body.witness_id, user.tenant_id)
    if witness.step_id != step_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Witness does not belong to this step",
        )

    # completed outcome requires verified witness
    if (
        body.outcome_type in _REQUIRES_VERIFIED
        and witness.verification_class != "verified"
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"outcome_type='{body.outcome_type}' requires verification_class='verified'",
        )

    # One outcome per step
    repo = OutcomeObjectRepo(db)
    existing = await repo.get_by_step(step_id, user.tenant_id)
    if existing:
        return existing

    outcome = OutcomeObject(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        step_id=step_id,
        witness_id=body.witness_id,
        outcome_type=body.outcome_type,
        outcome_timestamp=body.outcome_timestamp,
        notes=body.notes,
    )
    await repo.create(outcome)
    await audit.record(
        db, object_type="OutcomeObject", object_id=outcome.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create",
        metadata={"outcome_type": body.outcome_type},
    )
    return outcome


@router.get("/outcomes/{outcome_id}", response_model=OutcomeObjectResponse)
async def get_outcome(
    outcome_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> OutcomeObject:
    return await OutcomeObjectRepo(db).get_or_404(outcome_id, user.tenant_id)
