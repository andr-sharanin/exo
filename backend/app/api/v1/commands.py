import uuid
from datetime import datetime, timezone

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.command import Command
from app.models.task_analysis import TaskAnalysis
from app.repositories import CommandRepo
from app.schemas import CommandCreate, CommandResponse
from app.services import audit
from app.api.v1.secretary import get_arq

router = APIRouter(prefix="/commands", tags=["pipeline: command"])


class ConfirmCommandRequest(BaseModel):
    decision: str  # "confirmed" | "deferred"
    note: str | None = None


@router.post("", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
async def create_command(
    body: CommandCreate,
    db: TenantDB,
    user: CurrentUser,
    arq: ArqRedis = Depends(get_arq),
) -> Command:
    repo = CommandRepo(db)

    existing = await repo.get_by_idempotency_key(user.tenant_id, body.idempotency_key)
    if existing:
        return existing

    # Extract human-readable text for kernel analysis
    raw_input = body.raw_payload_ref if len(body.raw_payload_ref) < 1000 else body.raw_payload_ref[:500]

    cmd = Command(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        ingress_channel=body.ingress_channel,
        ingress_modality=body.ingress_modality,
        raw_payload_ref=body.raw_payload_ref,
        raw_input=raw_input,
        submitted_at=body.submitted_at,
        idempotency_key=body.idempotency_key,
        status="pending",
        kernel_status="pending_analysis",
    )
    await repo.create(cmd)
    await audit.record(
        db,
        object_type="Command",
        object_id=cmd.id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        action="create",
        to_status="pending",
    )

    # Trigger async kernel analysis — non-blocking, result arrives via SSE
    await arq.enqueue_job(
        "analyze_command_task",
        str(cmd.id),
        str(user.user_id),
        str(user.tenant_id),
        raw_input,
    )

    return cmd


@router.post("/{command_id}/confirm", status_code=200)
async def confirm_or_defer_command(
    command_id: uuid.UUID,
    body: ConfirmCommandRequest,
    db: TenantDB,
    user: CurrentUser,
) -> dict:
    """
    User reviews kernel analysis and confirms or defers the command.
    confirmed → command proceeds to pipeline (status stays "pending")
    deferred  → command status = "dismissed", kernel_status = "deferred"
    """
    if body.decision not in ("confirmed", "deferred"):
        raise HTTPException(400, "decision must be 'confirmed' or 'deferred'")

    cmd = await CommandRepo(db).get_or_404(command_id, user.tenant_id)
    if cmd.kernel_status not in ("pending_confirmation", "pending_analysis"):
        raise HTTPException(409, "Command is not awaiting confirmation")

    # Update analysis record
    analysis_q = select(TaskAnalysis).where(TaskAnalysis.command_id == command_id)
    analysis = (await db.execute(analysis_q)).scalar_one_or_none()
    if analysis:
        analysis.user_decision = body.decision
        analysis.user_note = body.note
        analysis.decided_at = datetime.now(timezone.utc)
        await db.flush()

    # Update command
    cmd.kernel_status = body.decision
    if body.decision == "deferred":
        cmd.status = "dismissed"
    await db.flush()

    return {
        "command_id": str(command_id),
        "kernel_status": body.decision,
        "command_status": cmd.status,
    }


@router.get("/{command_id}/analysis")
async def get_command_analysis(
    command_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> dict:
    """Get kernel analysis result for a command."""
    await CommandRepo(db).get_or_404(command_id, user.tenant_id)
    q = (
        select(TaskAnalysis)
        .where(TaskAnalysis.command_id == command_id)
        .order_by(TaskAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = (await db.execute(q)).scalar_one_or_none()
    if not analysis:
        return {"available": False}
    return {
        "available": True,
        "alignment_score": analysis.alignment_score,
        "recommendation": analysis.recommendation,
        "reasoning": analysis.reasoning,
        "conflicts": analysis.conflicts or [],
        "synergies": analysis.synergies or [],
        "confirm_required": analysis.confirm_required,
        "suggested_timing": analysis.suggested_timing,
        "defer_reason": analysis.defer_reason,
        "user_decision": analysis.user_decision,
    }


@router.get("/{command_id}", response_model=CommandResponse)
async def get_command(
    command_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> Command:
    return await CommandRepo(db).get_or_404(command_id, user.tenant_id)


@router.get("", response_model=list[CommandResponse])
async def list_commands(
    db: TenantDB,
    user: CurrentUser,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Command]:
    return await CommandRepo(db).list_by_tenant(
        user.tenant_id, status=status_filter, limit=limit, offset=offset
    )
