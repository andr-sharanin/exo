import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.system_mode import SystemMode
from app.repositories.energy_repos import SystemModeRepo
from app.schemas.energy_schemas import ModeSwitchRequest, SystemModeResponse
from app.services import audit

router = APIRouter(prefix="/mode", tags=["mode"])


def _build_response(record: SystemMode) -> SystemModeResponse:
    return SystemModeResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        user_id=record.user_id,
        mode=record.mode,
        previous_mode=record.previous_mode,
        switch_reason=record.switch_reason,
        is_system_suggested=record.is_system_suggested,
        switched_at=record.switched_at,
        created_at=record.created_at,
    )


@router.post("/switch", response_model=SystemModeResponse, status_code=status.HTTP_201_CREATED)
async def switch_mode(
    body: ModeSwitchRequest,
    db: TenantDB,
    user: CurrentUser,
) -> SystemModeResponse:
    """Switch the active system mode. Records previous mode for audit trail."""
    now = datetime.now(timezone.utc)
    repo = SystemModeRepo(db)

    current = await repo.get_current(user.tenant_id, user.user_id)
    previous_mode = current.mode if current else None

    record = SystemMode(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        mode=body.mode.value,
        previous_mode=previous_mode,
        switch_reason=body.reason,
        is_system_suggested=False,
        switched_at=now,
    )
    await repo.create(record)
    await audit.record(
        db,
        object_type="SystemMode",
        object_id=record.id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        action="switch",
        from_status=previous_mode,
        to_status=record.mode,
    )

    return _build_response(record)


@router.get("/current", response_model=SystemModeResponse)
async def get_current_mode(
    db: TenantDB,
    user: CurrentUser,
) -> SystemModeResponse:
    """Return the currently active system mode."""
    record = await SystemModeRepo(db).get_current(user.tenant_id, user.user_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No mode set — switch to a mode first",
        )
    return _build_response(record)
