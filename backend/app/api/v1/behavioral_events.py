import uuid
from typing import Any

from fastapi import APIRouter, status

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.behavioral_event import BehavioralEvent
from app.repositories import BehavioralEventRepo
from app.repositories.energy_repos import EnergyScoreRepo
from app.schemas import BehavioralEventCreate, BehavioralEventResponse
from app.services import audit
from app.services.behavioral_policy import BehavioralPolicyEngine
from app.services.energy import EnergyState

router = APIRouter(prefix="/behavioral-events", tags=["behavioral"])


@router.post("", response_model=BehavioralEventResponse, status_code=status.HTTP_201_CREATED)
async def record_behavioral_event(
    body: BehavioralEventCreate,
    db: TenantDB,
    user: CurrentUser,
) -> dict[str, Any]:
    event = BehavioralEvent(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        behavioral_event_type=body.behavioral_event_type,
        event_timestamp=body.event_timestamp,
        user_declared_flag=body.user_declared_flag,
        trigger_description=body.trigger_description,
        context_ref=body.context_ref,
        status="recorded",
        # sensitivity_class forced to high_sensitive by BehavioralEvent.__init__
    )
    repo = BehavioralEventRepo(db)
    await repo.create(event)
    await audit.record(
        db, object_type="BehavioralEvent", object_id=event.id,
        tenant_id=user.tenant_id, user_id=user.user_id,
        action="create", to_status="recorded",
    )

    # Evaluate behavioural policy — energy state modulates response intensity
    latest_score = await EnergyScoreRepo(db).get_latest(user.tenant_id, user.user_id)
    energy_state = EnergyState(latest_score.state) if latest_score else EnergyState.CONSTRAINED
    policy = BehavioralPolicyEngine.evaluate(event.behavioral_event_type, energy_state=energy_state)

    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "user_id": event.user_id,
        "status": event.status,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "schema_version": event.schema_version,
        "sensitivity_class": event.sensitivity_class,
        "behavioral_event_type": event.behavioral_event_type,
        "event_timestamp": event.event_timestamp,
        "user_declared_flag": event.user_declared_flag,
        "trigger_description": event.trigger_description,
        "context_ref": event.context_ref,
        "policy_response": {
            "action": policy.action,
            "delay_minutes": policy.delay_minutes,
            "reflection_prompt": policy.reflection_prompt,
            "alternative_suggestions": policy.alternative_suggestions,
        },
    }


@router.get("/{event_id}", response_model=BehavioralEventResponse)
async def get_behavioral_event(
    event_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> BehavioralEvent:
    return await BehavioralEventRepo(db).get_or_404(event_id, user.tenant_id)
