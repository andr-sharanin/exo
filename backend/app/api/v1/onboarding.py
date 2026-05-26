"""
Phase 5 — Kernel Calibration (Onboarding).

Endpoints:
  POST /onboarding/start       → create session, return all questions
  POST /onboarding/submit      → score answers, create ClientKernelProfile, 201
  GET  /onboarding/profile     → latest completed profile or 404
  POST /onboarding/recalibrate → re-compute defaults from recent behaviour
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, update

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.client_kernel_profile import ClientKernelProfile
from app.models.execution_session import ExecutionSession
from app.models.onboarding_session import OnboardingSession, OnboardingSessionStatus
from app.models.policy_kernel import PolicyKernel
from app.repositories.energy_repos import ClientKernelProfileRepo, EnergyDataRepo
from app.repositories.onboarding_repo import OnboardingSessionRepo
from app.schemas.energy_schemas import ClientKernelProfileResponse
from app.schemas.onboarding_schemas import (
    AnswerItem,
    OnboardingStartRequest,
    OnboardingStartResponse,
    OnboardingSubmitRequest,
    QuestionDTO,
    QuestionOptionDTO,
    RecalibrateRequest,
)
from app.services import audit
from app.services.onboarding import OnboardingMode, OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_question_dto(q) -> QuestionDTO:
    return QuestionDTO(
        question_id=q.question_id,
        scenario=q.scenario,
        options=[QuestionOptionDTO(option_id=o.option_id, text=o.text) for o in q.options],
    )


def _validate_answers(
    answers: list[AnswerItem], mode: OnboardingMode
) -> dict[str, str]:
    """
    Validate submitted answers against the question bank for the given mode.
    Returns {question_id: option_id} or raises HTTPException(422).
    """
    expected_ids = {q.question_id for q in OnboardingService.get_questions(mode)}
    submitted_ids = {a.question_id for a in answers}

    missing = expected_ids - submitted_ids
    extra = submitted_ids - expected_ids
    if missing or extra:
        detail_parts = []
        if missing:
            detail_parts.append(f"missing questions: {sorted(missing)}")
        if extra:
            detail_parts.append(f"unexpected questions: {sorted(extra)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="; ".join(detail_parts),
        )

    answers_dict = {a.question_id: a.option_id for a in answers}
    try:
        OnboardingService.score_answers(answers_dict)  # validates option IDs
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return answers_dict


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/start",
    response_model=OnboardingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_onboarding(
    body: OnboardingStartRequest,
    db: TenantDB,
    user: CurrentUser,
) -> OnboardingStartResponse:
    now = datetime.now(timezone.utc)
    session = OnboardingSession(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        mode=body.mode.value,
        status=OnboardingSessionStatus.IN_PROGRESS,
        started_at=now,
    )
    repo = OnboardingSessionRepo(db)
    await repo.create(session)
    await audit.record(
        db, object_type="OnboardingSession", object_id=session.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status=OnboardingSessionStatus.IN_PROGRESS,
    )

    questions = OnboardingService.get_questions(body.mode)
    return OnboardingStartResponse(
        session_id=session.id,
        mode=body.mode.value,
        questions=[_to_question_dto(q) for q in questions],
        total_questions=len(questions),
    )


@router.post(
    "/submit",
    response_model=ClientKernelProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_onboarding(
    body: OnboardingSubmitRequest,
    db: TenantDB,
    user: CurrentUser,
) -> ClientKernelProfile:
    repo = OnboardingSessionRepo(db)
    session = await repo.get_or_404(body.session_id, user.tenant_id)

    if session.status == OnboardingSessionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OnboardingSession already completed",
        )

    mode = OnboardingMode(session.mode)
    answers_dict = _validate_answers(body.answers, mode)

    dimension_scores = OnboardingService.score_answers(answers_dict)
    profile_data, computed_defaults = OnboardingService.compute_profile(dimension_scores)

    now = datetime.now(timezone.utc)

    # Determine calibration version (increment if prior profile exists)
    prior = await ClientKernelProfileRepo(db).get_latest(user.tenant_id, user.user_id)
    calibration_version = (prior.calibration_version + 1) if prior else 1

    profile = ClientKernelProfile(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        calibration_version=calibration_version,
        calibrated_at=now,
        profile_data=profile_data,
        computed_defaults=computed_defaults,
    )
    await ClientKernelProfileRepo(db).create(profile)
    await audit.record(
        db, object_type="ClientKernelProfile", object_id=profile.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status="calibrated",
    )

    # Mark session complete
    session.status = OnboardingSessionStatus.COMPLETED
    session.answers = answers_dict
    session.profile_id = profile.id
    session.completed_at = now
    await db.flush()
    await audit.record(
        db, object_type="OnboardingSession", object_id=session.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="complete", to_status=OnboardingSessionStatus.COMPLETED,
    )

    # Create PolicyKernel from onboarding profile (Phase 14)
    await _create_policy_kernel(
        db, user.tenant_id, user.user_id, profile_data, computed_defaults, answers_dict
    )

    return profile


async def _create_policy_kernel(
    db: TenantDB,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    profile_data: dict,
    computed_defaults: dict,
    raw_answers: dict,
) -> PolicyKernel:
    """Deactivate any existing PolicyKernel and create a new one from onboarding profile."""
    # Deactivate previous active kernels
    await db.execute(
        update(PolicyKernel)
        .where(PolicyKernel.user_id == user_id, PolicyKernel.is_active == True)  # noqa: E712
        .values(is_active=False)
    )

    prior_q = (
        select(PolicyKernel)
        .where(PolicyKernel.user_id == user_id)
        .order_by(PolicyKernel.version.desc())
        .limit(1)
    )
    prior = (await db.execute(prior_q)).scalar_one_or_none()
    version = (prior.version + 1) if prior else 1

    kernel = PolicyKernel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        version=version,
        is_active=True,
        calibration_source="onboarding",
        focus_stability=profile_data.get("focus_stability"),
        task_handling_style=profile_data.get("task_handling_style"),
        decision_style=profile_data.get("decision_style"),
        overload_threshold=profile_data.get("overload_threshold"),
        interruption_behavior=profile_data.get("interruption_behavior"),
        clarity_strategy=profile_data.get("clarity_strategy"),
        execution_pattern=profile_data.get("execution_pattern"),
        help_seeking_behavior=profile_data.get("help_seeking_behavior"),
        failure_response_pattern=profile_data.get("failure_response_pattern"),
        dominant_mode=computed_defaults.get("dominant_mode"),
        raw_answers=raw_answers,
        constraints=_derive_constraints(profile_data),
        strengths=_derive_strengths(profile_data),
    )
    db.add(kernel)
    await db.flush()
    return kernel


def _derive_constraints(p: dict) -> list[str]:
    out = []
    if p.get("focus_stability") == "low":
        out.append("Avoid tasks requiring uninterrupted focus longer than 30 minutes")
    if p.get("overload_threshold") == "low":
        out.append("Limit active task list to 3 items at a time")
    if p.get("decision_style") == "avoidant":
        out.append("Force a decision within 24 hours — do not defer indefinitely")
    if p.get("task_handling_style") == "parallel":
        out.append("Watch for context-switching overhead — batch similar work")
    return out


def _derive_strengths(p: dict) -> list[str]:
    out = []
    if p.get("focus_stability") == "high":
        out.append("Deep focus work — sustained long sessions")
    if p.get("execution_pattern") == "sprint":
        out.append("High-intensity burst execution — use for critical deadlines")
    if p.get("decision_style") == "fast":
        out.append("Rapid decision-making — iterate quickly, low regret")
    if p.get("help_seeking_behavior") == "proactive":
        out.append("Leverages network effectively — unblocks fast")
    if p.get("overload_threshold") == "high":
        out.append("Thrives under load — high-pressure environments")
    return out


@router.get("/profile", response_model=ClientKernelProfileResponse)
async def get_profile(
    db: TenantDB,
    user: CurrentUser,
) -> ClientKernelProfile:
    profile = await ClientKernelProfileRepo(db).get_latest(user.tenant_id, user.user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No calibration profile found — complete onboarding first",
        )
    return profile


@router.post(
    "/recalibrate",
    response_model=ClientKernelProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def recalibrate(
    db: TenantDB,
    user: CurrentUser,
    body: RecalibrateRequest = RecalibrateRequest(),
) -> ClientKernelProfile:
    prior = await ClientKernelProfileRepo(db).get_latest(user.tenant_id, user.user_id)
    if prior is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No calibration profile found — complete onboarding first",
        )

    lookback_days = body.lookback_days
    since = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=lookback_days)

    data_repo = EnergyDataRepo(db)
    urge_count = await data_repo.count_events_by_type_since(
        user.tenant_id, "urge_event", since
    )
    abandoned = await data_repo.count_abandoned_sessions_since(user.tenant_id, since)
    total_sessions_result = await db.execute(
        select(func.count())
        .select_from(ExecutionSession)
        .where(
            ExecutionSession.tenant_id == user.tenant_id,
            ExecutionSession.created_at >= since,
        )
    )
    total_sessions = total_sessions_result.scalar_one()
    completed = max(0, total_sessions - abandoned)

    updated_defaults = OnboardingService.recalibrate_defaults(
        dict(prior.computed_defaults),
        urge_events_last_30d=urge_count,
        abandoned_sessions_last_30d=abandoned,
        completed_sessions_last_30d=completed,
    )

    now = datetime.now(timezone.utc)
    new_profile = ClientKernelProfile(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        calibration_version=prior.calibration_version + 1,
        calibrated_at=now,
        profile_data=dict(prior.profile_data),
        computed_defaults=updated_defaults,
    )
    await ClientKernelProfileRepo(db).create(new_profile)
    await audit.record(
        db, object_type="ClientKernelProfile", object_id=new_profile.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="recalibrate", to_status="calibrated",
    )

    return new_profile
