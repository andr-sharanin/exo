"""
Habits API — track daily/weekly habits with streak calculation.

POST   /habits                  — create habit
GET    /habits                  — list habits with streak + checked_today
PUT    /habits/{id}             — update habit
DELETE /habits/{id}             — deactivate habit
POST   /habits/{id}/checkin     — mark done today (idempotent)
GET    /habits/{id}/history     — completion history (last 30 days)
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.habit import HabitDefinition, HabitEntry

router = APIRouter(prefix="/habits", tags=["habits"])


class HabitCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    frequency: str = "daily"
    target_days: list[int] | None = None
    target_time: str | None = None
    estimated_minutes: int = Field(default=10, ge=1, le=480)
    category: str | None = None
    goal_id: uuid.UUID | None = None
    include_in_plan: bool = True


class HabitUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    frequency: str | None = None
    target_days: list[int] | None = None
    target_time: str | None = None
    estimated_minutes: int | None = None
    category: str | None = None
    include_in_plan: bool | None = None


class CheckinRequest(BaseModel):
    note: str | None = None
    quality: int | None = Field(default=None, ge=1, le=5)


@router.post("", status_code=201)
async def create_habit(body: HabitCreate, db: TenantDB, user: CurrentUser) -> dict:
    habit = HabitDefinition(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title=body.title,
        description=body.description,
        frequency=body.frequency,
        target_days=body.target_days,
        target_time=body.target_time,
        estimated_minutes=body.estimated_minutes,
        category=body.category,
        goal_id=body.goal_id,
        include_in_plan=body.include_in_plan,
        is_active=True,
    )
    db.add(habit)
    await db.flush()
    await db.refresh(habit)
    await db.commit()
    return _habit_response(habit, streak=0, checked_today=False)


@router.get("")
async def list_habits(db: TenantDB, user: CurrentUser) -> list[dict]:
    q = (
        select(HabitDefinition)
        .where(
            HabitDefinition.user_id == user.user_id,
            HabitDefinition.is_active == True,  # noqa: E712
        )
        .order_by(HabitDefinition.created_at)
    )
    habits = list((await db.execute(q)).scalars().all())

    result = []
    for h in habits:
        streak = await _calculate_streak(str(h.id), db)
        checked = await _checked_today(str(h.id), db)
        result.append(_habit_response(h, streak, checked))
    return result


@router.put("/{habit_id}")
async def update_habit(
    habit_id: uuid.UUID, body: HabitUpdate, db: TenantDB, user: CurrentUser
) -> dict:
    habit = await _get_or_404(habit_id, user.user_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(habit, field, value)
    await db.flush()
    await db.commit()
    streak = await _calculate_streak(str(habit.id), db)
    checked = await _checked_today(str(habit.id), db)
    return _habit_response(habit, streak, checked)


@router.delete("/{habit_id}", status_code=204)
async def deactivate_habit(habit_id: uuid.UUID, db: TenantDB, user: CurrentUser) -> None:
    habit = await _get_or_404(habit_id, user.user_id, db)
    habit.is_active = False
    await db.flush()
    await db.commit()


@router.post("/{habit_id}/checkin")
async def checkin_habit(
    habit_id: uuid.UUID, body: CheckinRequest, db: TenantDB, user: CurrentUser
) -> dict:
    habit = await _get_or_404(habit_id, user.user_id, db)

    # Idempotent — reject duplicate same-day entry
    today = date.today()
    existing_q = select(HabitEntry).where(
        HabitEntry.habit_id == habit_id,
        func.date(HabitEntry.completed_at) == today,
    )
    if (await db.execute(existing_q)).scalar_one_or_none():
        streak = await _calculate_streak(str(habit_id), db)
        return {"streak": streak, "already_done": True, "message": "Already checked in today"}

    entry = HabitEntry(
        id=uuid.uuid4(),
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        habit_id=habit_id,
        completed_at=datetime.now(timezone.utc),
        note=body.note,
        quality=body.quality,
    )
    db.add(entry)
    await db.flush()
    await db.commit()
    streak = await _calculate_streak(str(habit_id), db)
    return {"streak": streak, "already_done": False}


@router.get("/{habit_id}/history")
async def habit_history(habit_id: uuid.UUID, db: TenantDB, user: CurrentUser) -> dict:
    await _get_or_404(habit_id, user.user_id, db)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    q = (
        select(HabitEntry)
        .where(
            HabitEntry.habit_id == habit_id,
            HabitEntry.completed_at >= cutoff,
        )
        .order_by(HabitEntry.completed_at.desc())
    )
    entries = list((await db.execute(q)).scalars().all())
    return {
        "entries": [
            {
                "date": e.completed_at.date().isoformat(),
                "quality": e.quality,
                "note": e.note,
            }
            for e in entries
        ],
        "total_30_days": len(entries),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(habit_id: uuid.UUID, user_id, db) -> HabitDefinition:
    q = select(HabitDefinition).where(
        HabitDefinition.id == habit_id,
        HabitDefinition.user_id == user_id,
    )
    habit = (await db.execute(q)).scalar_one_or_none()
    if not habit:
        raise HTTPException(404, "Habit not found")
    return habit


async def _calculate_streak(habit_id: str, db) -> int:
    """Count consecutive days with at least one entry (today or yesterday counts)."""
    q = (
        select(func.date(HabitEntry.completed_at).label("d"))
        .where(HabitEntry.habit_id == habit_id)
        .distinct()
        .order_by(func.date(HabitEntry.completed_at).desc())
    )
    rows = (await db.execute(q)).fetchall()
    dates = [r.d for r in rows]
    if not dates:
        return 0

    streak = 0
    check = date.today()
    for d in dates:
        if d == check or d == check - timedelta(days=1):
            streak += 1
            check = d - timedelta(days=1)
        else:
            break
    return streak


async def _checked_today(habit_id: str, db) -> bool:
    q = select(HabitEntry).where(
        HabitEntry.habit_id == habit_id,
        func.date(HabitEntry.completed_at) == date.today(),
    )
    return (await db.execute(q)).scalar_one_or_none() is not None


def _habit_response(h: HabitDefinition, streak: int, checked_today: bool) -> dict:
    return {
        "id": str(h.id),
        "title": h.title,
        "description": h.description,
        "frequency": h.frequency,
        "target_time": h.target_time,
        "estimated_minutes": h.estimated_minutes,
        "category": h.category,
        "include_in_plan": h.include_in_plan,
        "streak": streak,
        "checked_today": checked_today,
        "created_at": h.created_at.isoformat(),
    }
