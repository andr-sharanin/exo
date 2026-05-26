"""
Планёрки API — daily/weekly/monthly review sessions.

GET  /reviews/pending          — sessions awaiting user action (dashboard badge)
GET  /reviews/{id}             — session detail with AI agenda + questions
POST /reviews/{id}/start       — mark in_progress + record started_at
POST /reviews/{id}/complete    — submit answers, confirm plan, update kernels
POST /reviews/daily            — manually trigger daily review (if missed auto-creation)
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


class CompleteReviewRequest(BaseModel):
    answers: dict = {}
    plan_confirmed: bool = False
    plan_adjustments: list | None = None
    user_notes: str | None = None


@router.get("/pending")
async def get_pending_reviews(db: TenantDB, user: CurrentUser) -> list[dict]:
    """Return pending/in_progress sessions. Used for dashboard notification badge."""
    svc = ReviewService(db)
    sessions = await svc.get_pending(str(user.user_id))
    return [_session_summary(s) for s in sessions]


@router.get("/history")
async def get_review_history(
    db: TenantDB,
    user: CurrentUser,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Completed review sessions, newest first."""
    from sqlalchemy import select, desc
    from app.models.review_session import ReviewSession
    q = (
        select(ReviewSession)
        .where(
            ReviewSession.user_id == user.user_id,
            ReviewSession.status == "completed",
        )
        .order_by(desc(ReviewSession.completed_at))
        .limit(min(limit, 100))
        .offset(offset)
    )
    sessions = list((await db.execute(q)).scalars().all())
    return [_session_summary(s) for s in sessions]


@router.get("/{session_id}")
async def get_review_session(session_id: uuid.UUID, db: TenantDB, user: CurrentUser) -> dict:
    from sqlalchemy import select
    from app.models.review_session import ReviewSession
    q = select(ReviewSession).where(
        ReviewSession.id == session_id,
        ReviewSession.user_id == user.user_id,
    )
    session = (await db.execute(q)).scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Review session not found")
    return _session_detail(session)


@router.post("/{session_id}/start")
async def start_review(session_id: uuid.UUID, db: TenantDB, user: CurrentUser) -> dict:
    svc = ReviewService(db)
    session = await svc.start(str(session_id), str(user.user_id))
    await db.commit()
    return _session_summary(session)


@router.post("/{session_id}/complete")
async def complete_review(
    session_id: uuid.UUID,
    body: CompleteReviewRequest,
    db: TenantDB,
    user: CurrentUser,
) -> dict:
    svc = ReviewService(db)
    session = await svc.complete(
        session_id=str(session_id),
        user_id=str(user.user_id),
        tenant_id=str(user.tenant_id),
        answers=body.answers,
        plan_confirmed=body.plan_confirmed,
        plan_adjustments=body.plan_adjustments,
        user_notes=body.user_notes,
    )
    await db.commit()
    return _session_detail(session)


@router.post("/daily", status_code=202)
async def trigger_daily_review(db: TenantDB, user: CurrentUser) -> dict:
    """Manually create today's daily review (if ARQ job was missed)."""
    svc = ReviewService(db)
    session = await svc.create_daily_session(str(user.user_id), str(user.tenant_id))
    await db.commit()
    return {"session_id": str(session.id), "status": "created"}


# ── Serializers ───────────────────────────────────────────────────────────────

def _session_summary(s) -> dict:
    return {
        "id": str(s.id),
        "review_type": s.review_type,
        "status": s.status,
        "created_at": s.created_at.isoformat(),
        "has_ai_agenda": bool(s.ai_agenda),
        "plan_confirmed": s.plan_confirmed,
    }


def _session_detail(s) -> dict:
    return {
        **_session_summary(s),
        "ai_agenda": s.ai_agenda,
        "ai_plan_suggestion": s.ai_plan_suggestion,
        "questions": s.questions_snapshot,
        "answers": s.answers,
        "user_notes": s.user_notes,
        "plan_adjustments": s.plan_adjustments,
        "goals_updated": s.goals_updated,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "duration_seconds": s.duration_seconds,
    }
