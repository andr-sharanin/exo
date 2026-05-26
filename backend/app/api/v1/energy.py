import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.energy_score import EnergyScore
from app.repositories.energy_repos import EnergyDataRepo, EnergyScoreRepo, SystemModeRepo
from app.schemas.energy_schemas import (
    EnergyCheckinCreate,
    EnergyOverrideCreate,
    EnergyScoreResponse,
)
from app.services import audit
from app.services.energy import EnergyScoreEngine, EnergyState, IndirectSignals

router = APIRouter(prefix="/energy", tags=["energy"])

_VALID_HOURS = 24


def _build_response(record: EnergyScore, suggested_mode: str | None) -> EnergyScoreResponse:
    return EnergyScoreResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        user_id=record.user_id,
        score=record.score,
        state=record.state,
        is_override=record.is_override,
        valid_until=record.valid_until,
        created_at=record.created_at,
        suggested_mode=suggested_mode,
    )


async def _get_previous_state(
    repo: EnergyScoreRepo, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> EnergyState | None:
    previous = await repo.get_latest(tenant_id, user_id)
    return EnergyState(previous.state) if previous else None


async def _get_suggested_mode(
    mode_repo: SystemModeRepo,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    state: EnergyState,
) -> str | None:
    current = await mode_repo.get_current(tenant_id, user_id)
    current_name = current.mode if current else "harmony"
    return EnergyScoreEngine.suggest_mode(state, current_name)


@router.post("/checkin", response_model=EnergyScoreResponse, status_code=status.HTTP_201_CREATED)
async def energy_checkin(
    body: EnergyCheckinCreate,
    db: TenantDB,
    user: CurrentUser,
) -> EnergyScoreResponse:
    """Morning check-in: compute composite energy score from direct + indirect signals."""
    now = datetime.now(timezone.utc)
    score_repo = EnergyScoreRepo(db)

    previous_state = await _get_previous_state(score_repo, user.tenant_id, user.user_id)

    base = EnergyScoreEngine.compute_from_checkin(
        sleep=body.sleep_quality, mood=body.mood, energy=body.energy_level
    )

    data_repo = EnergyDataRepo(db)
    abandoned = await data_repo.count_abandoned_sessions_since(
        user.tenant_id, now - timedelta(hours=24)
    )
    urge_events = await data_repo.count_events_by_type_since(
        user.tenant_id, "urge_event", now - timedelta(hours=6)
    )
    lapse_events = await data_repo.count_events_by_type_since(
        user.tenant_id, "lapse_event", now - timedelta(hours=24)
    )

    signals = IndirectSignals(
        hour_of_day=now.hour,
        abandoned_sessions=abandoned,
        urge_events_6h=urge_events,
        defer_events_24h=lapse_events,
    )

    adjusted = EnergyScoreEngine.apply_indirect_signals(base, signals)
    state = EnergyScoreEngine.compute_state(adjusted, previous_state)

    suggested_mode = await _get_suggested_mode(
        SystemModeRepo(db), user.tenant_id, user.user_id, state
    )

    record = EnergyScore(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        score=adjusted,
        state=state.value,
        checkin_signals={
            "sleep_quality": body.sleep_quality,
            "mood": body.mood,
            "energy_level": body.energy_level,
            "note": body.note,
        },
        indirect_signals={
            "hour_of_day": signals.hour_of_day,
            "abandoned_sessions": signals.abandoned_sessions,
            "urge_events_6h": signals.urge_events_6h,
            "defer_events_24h": signals.defer_events_24h,
        },
        is_override=False,
        valid_until=now + timedelta(hours=_VALID_HOURS),
    )
    await score_repo.create(record)
    await audit.record(
        db,
        object_type="EnergyScore",
        object_id=record.id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        action="checkin",
        to_status=state.value,
    )

    return _build_response(record, suggested_mode)


@router.post("/override", response_model=EnergyScoreResponse, status_code=status.HTTP_201_CREATED)
async def energy_override(
    body: EnergyOverrideCreate,
    db: TenantDB,
    user: CurrentUser,
) -> EnergyScoreResponse:
    """Manual score override — bypasses check-in computation entirely."""
    now = datetime.now(timezone.utc)
    score_repo = EnergyScoreRepo(db)

    previous_state = await _get_previous_state(score_repo, user.tenant_id, user.user_id)
    state = EnergyScoreEngine.compute_state(body.score, previous_state)

    suggested_mode = await _get_suggested_mode(
        SystemModeRepo(db), user.tenant_id, user.user_id, state
    )

    record = EnergyScore(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        score=body.score,
        state=state.value,
        checkin_signals=None,
        indirect_signals=None,
        is_override=True,
        override_reason=body.reason,
        valid_until=now + timedelta(hours=_VALID_HOURS),
    )
    await score_repo.create(record)
    await audit.record(
        db,
        object_type="EnergyScore",
        object_id=record.id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        action="override",
        to_status=state.value,
    )

    return _build_response(record, suggested_mode)


@router.get("/score", response_model=EnergyScoreResponse)
async def get_current_score(
    db: TenantDB,
    user: CurrentUser,
) -> EnergyScoreResponse:
    """Return the most recent energy score for the authenticated user."""
    record = await EnergyScoreRepo(db).get_latest(user.tenant_id, user.user_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No energy score found — complete a check-in first",
        )
    return _build_response(record, suggested_mode=None)
