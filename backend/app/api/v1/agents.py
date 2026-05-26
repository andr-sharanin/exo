"""
Phase 7 — Agents API

POST   /agents/sessions                       — create entity session
POST   /agents/sessions/{id}/message          — send user message, get assistant reply
GET    /agents/sessions/{id}/messages         — conversation history
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.agent_message import AgentMessage
from app.models.entity_session import EntitySession
from app.repositories.agent_repos import AgentMessageRepo
from app.repositories.pipeline_repos import EntitySessionRepo
from app.schemas.agent_schemas import (
    AgentMessageCreate,
    AgentMessageResponse,
    AgentSessionCreate,
    AgentSessionResponse,
)
from app.services.agents import AgentService, DEFAULT_ENTITY_TYPES
from app.services.fsm import EntitySessionStatus

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/sessions", response_model=AgentSessionResponse, status_code=201)
async def create_session(
    body: AgentSessionCreate, db: TenantDB, user: CurrentUser
) -> AgentSessionResponse:
    now = datetime.now(timezone.utc)
    session = await EntitySessionRepo(db).create(
        EntitySession(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            status=EntitySessionStatus.ACTIVE,
            entity_type=body.entity_type,
            session_mode=body.session_mode,
            context_ref=None,
            session_started_at=now,
        )
    )
    return AgentSessionResponse.model_validate(session)


@router.post(
    "/sessions/{session_id}/message",
    response_model=AgentMessageResponse,
    status_code=201,
)
async def send_message(
    session_id: uuid.UUID,
    body: AgentMessageCreate,
    db: TenantDB,
    user: CurrentUser,
) -> AgentMessageResponse:
    session = await EntitySessionRepo(db).get_or_404(session_id, user.tenant_id)
    msg_repo = AgentMessageRepo(db)

    history_records = await msg_repo.get_by_session(session_id)
    history = [{"role": m.role, "content": m.content} for m in history_records]
    next_order = len(history_records)

    # Save user message
    await msg_repo.create(
        AgentMessage(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            session_id=session_id,
            role="user",
            content=body.content,
            message_order=next_order,
            model_used=None,
            latency_ms=0,
        )
    )

    # Call AI — use DB-backed AgentService (dynamic personas)
    svc = AgentService(db)
    ai_response = await svc.chat(
        entity_type=session.entity_type,
        tenant_id=str(user.tenant_id),
        history=history,
        user_content=body.content,
        task_context=body.task_context if hasattr(body, "task_context") else None,
    )

    # Save assistant reply
    assistant_msg = await msg_repo.create(
        AgentMessage(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            session_id=session_id,
            role="assistant",
            content=ai_response.content,
            message_order=next_order + 1,
            model_used=ai_response.model_used,
            latency_ms=ai_response.latency_ms,
        )
    )
    return AgentMessageResponse.model_validate(assistant_msg)


@router.get("/sessions/{session_id}/messages", response_model=list[AgentMessageResponse])
async def get_messages(
    session_id: uuid.UUID, db: TenantDB, user: CurrentUser
) -> list[AgentMessageResponse]:
    await EntitySessionRepo(db).get_or_404(session_id, user.tenant_id)
    messages = await AgentMessageRepo(db).get_by_session(session_id)
    return [AgentMessageResponse.model_validate(m) for m in messages]
