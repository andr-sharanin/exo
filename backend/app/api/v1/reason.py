import uuid

from fastapi import APIRouter, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.reasoning_artifact import ReasoningArtifact
from app.repositories import CaptureRecordRepo, ReasoningArtifactRepo
from app.schemas import ReasoningArtifactCreate, ReasoningArtifactResponse
from app.services import audit

router = APIRouter(tags=["pipeline: reason"])


@router.post(
    "/capture/{capture_id}/reason",
    response_model=ReasoningArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reasoning_artifact(
    capture_id: uuid.UUID,
    body: ReasoningArtifactCreate,
    db: TenantDB,
    user: CurrentUser,
) -> ReasoningArtifact:
    await CaptureRecordRepo(db).get_or_404(capture_id, user.tenant_id)

    repo = ReasoningArtifactRepo(db)
    existing = await repo.get_by_capture(capture_id, user.tenant_id)
    if existing:
        return existing

    artifact = ReasoningArtifact(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        capture_id=capture_id,
        reasoning_stage=body.reasoning_stage,
        intent_hypothesis=body.intent_hypothesis,
        ambiguity_level=body.ambiguity_level,
        actionability_status=body.actionability_status,
        reasoning_model_role=body.reasoning_model_role,
        status="pending",
    )
    await repo.create(artifact)
    await audit.record(
        db, object_type="ReasoningArtifact", object_id=artifact.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status="pending",
    )
    return artifact


@router.get("/reason/{artifact_id}", response_model=ReasoningArtifactResponse)
async def get_reasoning_artifact(
    artifact_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> ReasoningArtifact:
    return await ReasoningArtifactRepo(db).get_or_404(artifact_id, user.tenant_id)
