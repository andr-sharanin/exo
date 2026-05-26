"""
Phase 8 — Commitment Deposits API

POST   /deposits              — create deposit for a step
GET    /deposits              — list deposits for current user
POST   /deposits/{id}/release — mark released (task completed on time) → 409 if not held
POST   /deposits/{id}/forfeit — mark forfeited (deadline missed)       → 409 if not held
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.commitment_deposit import CommitmentDeposit
from app.repositories.deposit_repos import CommitmentDepositRepo
from app.schemas.deposit_schemas import CommitmentDepositCreate, CommitmentDepositResponse

router = APIRouter(prefix="/deposits", tags=["deposits"])


@router.post("", response_model=CommitmentDepositResponse, status_code=201)
async def create_deposit(
    body: CommitmentDepositCreate, db: TenantDB, user: CurrentUser
) -> CommitmentDepositResponse:
    from app.services.subscription_service import SubscriptionService
    await SubscriptionService(db).assert_can_create_deposit(user.user_id, user.tenant_id)

    deposit = await CommitmentDepositRepo(db).create(
        CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            step_id=body.step_id,
            amount_cents=body.amount_cents,
            currency=body.currency,
            status="held",
            due_date=body.due_date,
        )
    )
    return CommitmentDepositResponse.model_validate(deposit)


@router.get("", response_model=list[CommitmentDepositResponse])
async def list_deposits(db: TenantDB, user: CurrentUser) -> list[CommitmentDepositResponse]:
    deposits = await CommitmentDepositRepo(db).list_by_user(user.tenant_id, user.user_id)
    return [CommitmentDepositResponse.model_validate(d) for d in deposits]


@router.post("/{deposit_id}/release", response_model=CommitmentDepositResponse)
async def release_deposit(
    deposit_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> CommitmentDepositResponse:
    repo = CommitmentDepositRepo(db)
    deposit = await repo.get_or_404(deposit_id, user.tenant_id)
    if deposit.status != "held":
        raise HTTPException(status_code=409, detail="Deposit is not in held status")
    deposit.status = "released"
    deposit.released_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(deposit)
    return CommitmentDepositResponse.model_validate(deposit)


@router.post("/{deposit_id}/forfeit", response_model=CommitmentDepositResponse)
async def forfeit_deposit(
    deposit_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> CommitmentDepositResponse:
    repo = CommitmentDepositRepo(db)
    deposit = await repo.get_or_404(deposit_id, user.tenant_id)
    if deposit.status != "held":
        raise HTTPException(status_code=409, detail="Deposit is not in held status")
    deposit.status = "forfeited"
    deposit.forfeited_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(deposit)
    return CommitmentDepositResponse.model_validate(deposit)
