"""
Morning Brief Service — compiles a daily AI briefing from context snapshots.

Generated once per day per user, cached in Redis for 6 hours.
Cache key: brief:{user_id}:{YYYY-MM-DD}

Called by:
  - ARQ worker: generate_morning_brief_task (scheduled or on-demand)
  - API: GET /brief/today — reads cache, falls back to sync generation
"""
from __future__ import annotations

import json
from datetime import date, timedelta, timezone, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_client import AIClient

_CACHE_TTL_SECONDS = 6 * 3600
_BRIEF_SYSTEM = """You are an executive morning briefing assistant.
Compile a concise daily brief from the user's data.

Respond ONLY in valid JSON with this structure:
{
  "greeting": "<one energetic sentence to start the day>",
  "bullets": [
    {"emoji": "⚡", "text": "<key point 1>"},
    ...
  ],
  "focus_recommendation": "<1 sentence: the single most important thing to do first>",
  "energy_tip": "<1 sentence: energy/mode advice based on current state>"
}

Rules:
- 3-5 bullets maximum
- Be direct and actionable, not vague
- Respond in the same language as the user's data (default: Russian)
- If data is sparse, generate motivating defaults"""


class MorningBriefService:
    def __init__(self, db: AsyncSession, redis) -> None:
        self.db = db
        self.redis = redis
        self.ai = AIClient(db)

    async def generate(self, user_id: str, tenant_id: str) -> dict:
        """Generate brief, cache it, return it."""
        cache_key = self._cache_key(user_id)

        context = await self._build_context(user_id)
        try:
            raw = await self.ai.complete(
                system=_BRIEF_SYSTEM,
                user=f"User context for morning brief:\n{json.dumps(context, ensure_ascii=False, indent=2)}",
                tier=2,
            )
            brief = json.loads(raw)
        except Exception:
            brief = _default_brief()

        brief["generated_at"] = datetime.now(timezone.utc).isoformat()
        brief["date"] = date.today().isoformat()

        await self.redis.setex(cache_key, _CACHE_TTL_SECONDS, json.dumps(brief, ensure_ascii=False))
        return brief

    async def get_cached(self, user_id: str) -> dict | None:
        """Return cached brief for today, or None if not yet generated."""
        cached = await self.redis.get(self._cache_key(user_id))
        if cached:
            raw = cached if isinstance(cached, str) else cached.decode()
            return json.loads(raw)
        return None

    async def invalidate(self, user_id: str) -> None:
        """Force regeneration on next request."""
        await self.redis.delete(self._cache_key(user_id))

    def _cache_key(self, user_id: str) -> str:
        return f"brief:{user_id}:{date.today().isoformat()}"

    async def _build_context(self, user_id: str) -> dict:
        from app.models.energy_score import EnergyScore
        from app.models.day_plan import DayPlan
        from app.models.habit import HabitDefinition, HabitEntry
        from app.models.command import Command
        from app.models.planning_goal import PlanningGoal

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Latest energy score
        energy_q = (
            select(EnergyScore)
            .where(EnergyScore.user_id == user_id)
            .order_by(EnergyScore.created_at.desc())
            .limit(1)
        )
        energy = (await self.db.execute(energy_q)).scalar_one_or_none()

        # Today's plan
        plan_q = (
            select(DayPlan)
            .where(DayPlan.user_id == user_id, DayPlan.plan_date == today)
            .limit(1)
        )
        plan = (await self.db.execute(plan_q)).scalar_one_or_none()

        # Pending confirmations (kernel filter waiting on user)
        pending_q = (
            select(Command)
            .where(
                Command.user_id == user_id,
                Command.kernel_status == "pending_confirmation",
            )
            .limit(5)
        )
        pending_commands = (await self.db.execute(pending_q)).scalars().all()

        # Active habits due today
        habits_q = select(HabitDefinition).where(
            HabitDefinition.user_id == user_id,
            HabitDefinition.is_active == True,  # noqa: E712
        )
        habits = (await self.db.execute(habits_q)).scalars().all()

        # Check which habits already have an entry today
        if habits:
            habit_ids = [h.id for h in habits]
            day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
            done_q = select(HabitEntry.habit_id).where(
                HabitEntry.habit_id.in_(habit_ids),
                HabitEntry.completed_at >= day_start,
            )
            done_ids = {row[0] for row in (await self.db.execute(done_q)).all()}
            pending_habits = [h.title for h in habits if h.id not in done_ids]
        else:
            pending_habits = []

        # Top active goals
        goals_q = (
            select(PlanningGoal)
            .where(PlanningGoal.user_id == user_id, PlanningGoal.status == "active")
            .order_by(PlanningGoal.created_at.desc())
            .limit(3)
        )
        goals = (await self.db.execute(goals_q)).scalars().all()

        return {
            "date": today.isoformat(),
            "energy_state": energy.state if energy else "unknown",
            "energy_score": energy.score if energy else None,
            "plan_items_count": len(plan.items or []) if plan else 0,
            "plan_status": plan.status if plan else "not_generated",
            "plan_preview": (plan.items or [])[:3] if plan else [],
            "pending_confirmations": len(pending_commands),
            "pending_habits": pending_habits,
            "active_goals": [{"title": g.title, "horizon": g.horizon} for g in goals],
        }


def _default_brief() -> dict:
    return {
        "greeting": "Доброе утро! Начнём день с ясным фокусом.",
        "bullets": [
            {"emoji": "🎯", "text": "Открой план дня и выбери главную задачу"},
            {"emoji": "⚡", "text": "Сделай energy check-in для точного планирования"},
        ],
        "focus_recommendation": "Начни с самой важной задачи в первые 90 минут.",
        "energy_tip": "Следи за уровнем энергии — это ключ к продуктивному дню.",
    }
