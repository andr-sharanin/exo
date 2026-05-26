"""
Governance API — Architecture Decision Records (ADR)

GET  /governance/policy          — get current governance settings
PUT  /governance/policy          — update settings (mode + partner email)
POST /governance/records         — create ADR (for any reversal/deferral)
GET  /governance/records         — list ADRs (paginated)
POST /governance/records/{id}/approve  — partner approves (via token from email)
"""
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.governance import GovernanceRecord, GovernanceSetting

router = APIRouter(prefix="/governance", tags=["governance"])

from sqlalchemy import select


# ── Schemas ───────────────────────────────────────────────────────────────────

class PolicyUpdate(BaseModel):
    mode: str = Field(..., pattern="^(solo|x2)$")
    partner_email: str | None = Field(None, max_length=320)


class PolicyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    mode: str
    partner_email: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecordCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=512)
    reason: str = Field(..., min_length=20, max_length=5000,
                         description="Written justification — minimum 20 characters")


class RecordResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    subject: str
    reason: str
    mode_at_time: str
    partner_email: str | None
    status: str
    approved_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_setting(db, tenant_id, user_id) -> GovernanceSetting | None:
    result = await db.execute(
        select(GovernanceSetting).where(
            GovernanceSetting.user_id == user_id,
            GovernanceSetting.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def _send_approval_email(partner_email: str, record_id: uuid.UUID, token: str) -> None:
    """Stub — log approval request. Replace with SMTP/SES in production."""
    import logging
    logging.getLogger(__name__).info(
        "Governance approval requested | record_id=%s partner=%s token=%s",
        record_id, partner_email, token,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/policy", response_model=PolicyResponse)
async def get_policy(db: TenantDB, user: CurrentUser):
    setting = await _get_setting(db, user.tenant_id, user.user_id)
    if setting is None:
        now = datetime.now(timezone.utc)
        return PolicyResponse(
            id=uuid.uuid4(),
            user_id=user.user_id,
            mode="solo",
            partner_email=None,
            created_at=now,
            updated_at=now,
        )
    return setting


@router.put("/policy", response_model=PolicyResponse, status_code=status.HTTP_200_OK)
async def update_policy(
    body: PolicyUpdate,
    db: TenantDB,
    user: CurrentUser,
) -> GovernanceSetting:
    if body.mode == "x2" and not body.partner_email:
        raise HTTPException(400, "partner_email is required when mode is x2")
    if body.mode == "x2":
        from app.services.subscription_service import SubscriptionService
        await SubscriptionService(db).assert_can_use_x2_governance(user.user_id, user.tenant_id)

    setting = await _get_setting(db, user.tenant_id, user.user_id)
    now = datetime.now(timezone.utc)
    if setting is None:
        setting = GovernanceSetting(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            mode=body.mode,
            partner_email=body.partner_email,
            created_at=now,
            updated_at=now,
        )
        db.add(setting)
    else:
        setting.mode = body.mode
        setting.partner_email = body.partner_email
        setting.updated_at = now
    await db.flush()
    return setting


@router.post("/records", response_model=RecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record(
    body: RecordCreate,
    db: TenantDB,
    user: CurrentUser,
) -> GovernanceRecord:
    setting = await _get_setting(db, user.tenant_id, user.user_id)
    mode = setting.mode if setting else "solo"
    partner_email = setting.partner_email if setting else None
    now = datetime.now(timezone.utc)

    if mode == "x2" and not partner_email:
        raise HTTPException(400, "Governance mode is x2 but no partner_email configured. Update governance policy first.")

    token: str | None = None
    rec_status = "self_approved"
    approved_at: datetime | None = now

    if mode == "x2":
        token = secrets.token_urlsafe(32)
        rec_status = "pending_partner"
        approved_at = None

    record = GovernanceRecord(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        subject=body.subject,
        reason=body.reason,
        mode_at_time=mode,
        partner_email=partner_email,
        approval_token=token,
        status=rec_status,
        approved_at=approved_at,
        created_at=now,
    )
    db.add(record)
    await db.flush()

    if mode == "x2" and partner_email and token:
        await _send_approval_email(partner_email, record.id, token)

    return record


@router.get("/records", response_model=list[RecordResponse])
async def list_records(
    db: TenantDB,
    user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[GovernanceRecord]:
    result = await db.execute(
        select(GovernanceRecord)
        .where(
            GovernanceRecord.tenant_id == user.tenant_id,
            GovernanceRecord.user_id == user.user_id,
        )
        .order_by(GovernanceRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.post("/records/{record_id}/approve", response_model=RecordResponse)
async def approve_record(
    record_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
    token: str = Query(..., description="Approval token sent to partner email"),
) -> GovernanceRecord:
    result = await db.execute(
        select(GovernanceRecord).where(
            GovernanceRecord.id == record_id,
            GovernanceRecord.tenant_id == user.tenant_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "Record not found")
    if record.status != "pending_partner":
        raise HTTPException(409, f"Record is already '{record.status}'")
    if record.approval_token != token:
        raise HTTPException(403, "Invalid approval token")

    record.status = "partner_approved"
    record.approved_at = datetime.now(timezone.utc)
    record.approval_token = None  # one-time use
    await db.flush()
    return record
