import uuid

from fastapi import APIRouter, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.capture_record import CaptureRecord
from app.repositories import CaptureRecordRepo, CommandRepo
from app.schemas import CaptureRecordCreate, CaptureRecordResponse
from app.services import audit, fsm

router = APIRouter(tags=["pipeline: capture"])


@router.post(
    "/commands/{command_id}/capture",
    response_model=CaptureRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_capture_record(
    command_id: uuid.UUID,
    body: CaptureRecordCreate,
    db: TenantDB,
    user: CurrentUser,
) -> CaptureRecord:
    cmd_repo = CommandRepo(db)
    cap_repo = CaptureRecordRepo(db)

    cmd = await cmd_repo.get_or_404(command_id, user.tenant_id)

    # Idempotent: return existing if already captured
    existing = await cap_repo.get_by_command(command_id, user.tenant_id)
    if existing:
        return existing

    # Transition Command: pending → captured
    old_status = cmd.status
    cmd.status = fsm.transition("Command", cmd.status, "capture")
    await audit.record(
        db, object_type="Command", object_id=cmd.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="capture", from_status=old_status, to_status=cmd.status,
    )

    cap = CaptureRecord(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        command_id=command_id,
        raw_payload_ref=body.raw_payload_ref,
        attachment_bundle_ref=body.attachment_bundle_ref,
        capture_integrity_status=body.capture_integrity_status,
        capture_hash=body.capture_hash,
        status="pending",
    )
    await cap_repo.create(cap)
    await audit.record(
        db, object_type="CaptureRecord", object_id=cap.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status="pending",
    )
    return cap


@router.get("/capture/{capture_id}", response_model=CaptureRecordResponse)
async def get_capture_record(
    capture_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> CaptureRecord:
    return await CaptureRecordRepo(db).get_or_404(capture_id, user.tenant_id)
