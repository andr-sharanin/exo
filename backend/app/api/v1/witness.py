import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.witness_object import WitnessObject
from app.repositories import StepObjectRepo, WitnessObjectRepo
from app.schemas import WitnessObjectCreate, WitnessObjectResponse
from app.services import audit

router = APIRouter(tags=["pipeline: witness"])

# manual witness cannot produce 'verified' — KDC §7 constraint
_MANUAL_FORBIDDEN_CLASSES = {"verified"}


@router.post(
    "/steps/{step_id}/witness",
    response_model=WitnessObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_witness(
    step_id: uuid.UUID,
    body: WitnessObjectCreate,
    db: TenantDB,
    user: CurrentUser,
) -> WitnessObject:
    await StepObjectRepo(db).get_or_404(step_id, user.tenant_id)

    if (
        body.witness_type == "manual"
        and body.verification_class in _MANUAL_FORBIDDEN_CLASSES
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Manual witness cannot produce 'verified' — only 'reported' or 'partial'",
        )

    repo = WitnessObjectRepo(db)
    existing = await repo.get_by_step(step_id, user.tenant_id)
    if existing:
        return existing

    witness = WitnessObject(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        step_id=step_id,
        execution_session_id=body.execution_session_id,
        witness_type=body.witness_type,
        witness_timestamp=body.witness_timestamp,
        verification_class=body.verification_class,
        evidence_ref=body.evidence_ref,
        status="pending",
    )
    await repo.create(witness)
    await audit.record(
        db, object_type="WitnessObject", object_id=witness.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status="pending",
    )
    return witness


@router.get("/witness/{witness_id}", response_model=WitnessObjectResponse)
async def get_witness(
    witness_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> WitnessObject:
    return await WitnessObjectRepo(db).get_or_404(witness_id, user.tenant_id)
