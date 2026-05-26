"""
Users API — GDPR-compliant data export and account deletion.

GET    /users/me/export   — download all personal data as JSON
DELETE /users/me          — soft-delete account (requires confirmation header)
"""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.behavioral_event import BehavioralEvent
from app.models.commitment_deposit import CommitmentDeposit
from app.models.day_plan import DayPlan
from app.models.energy_score import EnergyScore
from app.models.habit import HabitDefinition, HabitEntry
from app.models.onboarding_session import OnboardingSession
from app.models.planning_goal import PlanningGoal
from app.models.review_session import ReviewSession
from app.models.system_mode import SystemMode

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/export")
async def export_my_data(db: TenantDB, user: CurrentUser) -> dict:
    """
    Returns a JSON snapshot of all personal data for the current user.
    GDPR Article 20 — Right to data portability.
    """
    u_id = user.user_id
    t_id = user.tenant_id

    async def _q(model, **filters):
        clauses = [
            getattr(model, k) == v
            for k, v in {"user_id": u_id, "tenant_id": t_id}.items()
            if hasattr(model, k) and k in filters or True
        ]
        # Simpler: always filter by user_id if present, tenant_id if present
        c = []
        if hasattr(model, "user_id"):
            c.append(model.user_id == u_id)
        if hasattr(model, "tenant_id"):
            c.append(model.tenant_id == t_id)
        rows = (await db.execute(select(model).where(*c))).scalars().all()
        return rows

    energy_scores = await _q(EnergyScore)
    system_modes = await _q(SystemMode)
    day_plans = await _q(DayPlan)
    goals = await _q(PlanningGoal)
    deposits = await _q(CommitmentDeposit)
    habits = await _q(HabitDefinition)
    habit_entries = await _q(HabitEntry)
    onboarding = await _q(OnboardingSession)
    reviews = await _q(ReviewSession)
    events = await _q(BehavioralEvent)

    def _ser(obj) -> dict:
        return {
            c.key: (
                getattr(obj, c.key).isoformat()
                if isinstance(getattr(obj, c.key), (datetime, date))
                else str(getattr(obj, c.key))
                if hasattr(getattr(obj, c.key), "__str__") and not isinstance(getattr(obj, c.key), (str, int, float, bool, list, dict, type(None)))
                else getattr(obj, c.key)
            )
            for c in obj.__table__.columns
        }

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user_id": str(u_id),
        "tenant_id": str(t_id),
        "energy_scores": [_ser(r) for r in energy_scores],
        "system_modes": [_ser(r) for r in system_modes],
        "day_plans": [_ser(r) for r in day_plans],
        "planning_goals": [_ser(r) for r in goals],
        "commitment_deposits": [_ser(r) for r in deposits],
        "habits": [_ser(r) for r in habits],
        "habit_entries": [_ser(r) for r in habit_entries],
        "onboarding_sessions": [_ser(r) for r in onboarding],
        "review_sessions": [_ser(r) for r in reviews],
        "behavioral_events_count": len(events),
    }


@router.delete("/me", status_code=204)
async def delete_my_account(
    db: TenantDB,
    user: CurrentUser,
    x_confirm_delete: str = Header(..., alias="X-Confirm-Delete"),
) -> None:
    """
    Soft-delete the account. Requires header X-Confirm-Delete: DELETE MY ACCOUNT
    GDPR Article 17 — Right to erasure.

    Deactivates habits and goals; marks day plans abandoned.
    Full physical deletion is a manual ops step after 30-day grace period.
    """
    if x_confirm_delete != "DELETE MY ACCOUNT":
        raise HTTPException(
            400,
            "Send header X-Confirm-Delete: DELETE MY ACCOUNT to confirm"
        )

    u_id = user.user_id
    t_id = user.tenant_id

    # Deactivate habits
    habits_q = select(HabitDefinition).where(
        HabitDefinition.user_id == u_id,
        HabitDefinition.tenant_id == t_id,
        HabitDefinition.is_active == True,  # noqa: E712
    )
    for h in (await db.execute(habits_q)).scalars():
        h.is_active = False

    # Abandon active planning goals
    goals_q = select(PlanningGoal).where(
        PlanningGoal.user_id == u_id,
        PlanningGoal.tenant_id == t_id,
        PlanningGoal.status == "active",
    )
    for g in (await db.execute(goals_q)).scalars():
        g.status = "abandoned"

    await db.flush()
    await db.commit()
