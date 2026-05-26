"""
Review Service — handles daily/weekly/monthly планёрки.

Daily планёрка (Parabellum principle):
    - ARQ creates session at 07:00 every morning
    - AI prepares: energy state + today's tasks + risks + ordered plan suggestion
    - User opens the session → reviews AI brief → confirms or adjusts plan
    - After confirmation: no more thinking today, just execute

Weekly планёрка:
    - Created Friday 18:00
    - User reviews week: what was done, what wasn't, why
    - Updates weekly_focus in StrategicKernel

Monthly планёрка:
    - Created last day of month 09:00
    - Strategic recalibration → rebuilds StrategicKernel
"""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_session import ReviewSession
from app.models.review_template import ReviewTemplate
from app.models.strategic_kernel import StrategicKernel
from app.services.ai_client import AIClient


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai = AIClient(db)

    async def create_daily_session(self, user_id: str, tenant_id: str) -> ReviewSession:
        """Called by ARQ at 07:00. Creates daily планёрка with AI agenda."""
        template = await self._get_template("daily")
        agenda, plan = await self._prepare_daily_agenda(user_id, tenant_id)

        session = ReviewSession(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            review_type="daily",
            status="pending",
            template_id=template.id if template else None,
            questions_snapshot=template.questions if template else _DEFAULT_DAILY_QUESTIONS,
            ai_agenda=agenda,
            ai_plan_suggestion=plan,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def create_weekly_session(self, user_id: str, tenant_id: str) -> ReviewSession:
        template = await self._get_template("weekly")
        agenda = await self._prepare_weekly_agenda(user_id, tenant_id)

        session = ReviewSession(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            review_type="weekly",
            status="pending",
            template_id=template.id if template else None,
            questions_snapshot=template.questions if template else None,
            ai_agenda=agenda,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def create_monthly_session(self, user_id: str, tenant_id: str) -> ReviewSession:
        template = await self._get_template("monthly")
        agenda = await self._prepare_monthly_agenda(user_id, tenant_id)

        session = ReviewSession(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            review_type="monthly",
            status="pending",
            template_id=template.id if template else None,
            questions_snapshot=template.questions if template else None,
            ai_agenda=agenda,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def start(self, session_id: str, user_id: str) -> ReviewSession:
        session = await self._get_or_404(session_id, user_id)
        if session.status != "pending":
            return session
        session.status = "in_progress"
        session.started_at = datetime.now(timezone.utc)
        await self.db.flush()
        return session

    async def complete(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        answers: dict,
        plan_confirmed: bool = False,
        plan_adjustments: list | None = None,
        user_notes: str | None = None,
    ) -> ReviewSession:
        session = await self._get_or_404(session_id, user_id)
        now = datetime.now(timezone.utc)
        started = session.started_at or session.created_at

        session.status = "completed"
        session.answers = answers
        session.plan_confirmed = plan_confirmed
        session.plan_adjustments = plan_adjustments
        session.user_notes = user_notes
        session.completed_at = now
        session.duration_seconds = int((now - started).total_seconds())

        # Weekly/monthly → rebuild StrategicKernel
        if session.review_type in ("weekly", "monthly"):
            await self._update_strategic_kernel(
                user_id, tenant_id, session, answers
            )
            session.goals_updated = True

        await self.db.flush()
        return session

    async def get_pending(self, user_id: str) -> list[ReviewSession]:
        """Return all pending/in_progress sessions for dashboard notification."""
        q = (
            select(ReviewSession)
            .where(
                ReviewSession.user_id == user_id,
                ReviewSession.status.in_(["pending", "in_progress"]),
            )
            .order_by(ReviewSession.created_at.desc())
        )
        return list((await self.db.execute(q)).scalars().all())

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_template(self, review_type: str) -> ReviewTemplate | None:
        q = (
            select(ReviewTemplate)
            .where(
                ReviewTemplate.review_type == review_type,
                ReviewTemplate.is_active == True,  # noqa: E712
                ReviewTemplate.is_default == True,  # noqa: E712
            )
            .limit(1)
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def _get_or_404(self, session_id: str, user_id: str) -> ReviewSession:
        from fastapi import HTTPException
        q = select(ReviewSession).where(
            ReviewSession.id == session_id,
            ReviewSession.user_id == user_id,
        )
        session = (await self.db.execute(q)).scalar_one_or_none()
        if not session:
            raise HTTPException(404, "Review session not found")
        return session

    async def _prepare_daily_agenda(
        self, user_id: str, tenant_id: str
    ) -> tuple[str, list]:
        """Build AI morning brief + ordered plan suggestion."""
        context = await self._build_daily_context(user_id)
        try:
            raw = await self.ai.complete(
                system=_DAILY_AI_SYSTEM,
                user=f"Context:\n{json.dumps(context, ensure_ascii=False, indent=2)}",
                tier=2,
            )
            data = json.loads(raw)
            return data.get("agenda", ""), data.get("plan", [])
        except Exception:
            return "AI agenda unavailable — check your tasks manually.", []

    async def _prepare_weekly_agenda(self, user_id: str, tenant_id: str) -> str:
        context = await self._build_weekly_context(user_id)
        try:
            return await self.ai.complete(
                system=_WEEKLY_AI_SYSTEM,
                user=f"Weekly context:\n{json.dumps(context, ensure_ascii=False, indent=2)}",
                tier=2,
            )
        except Exception:
            return "Weekly analysis unavailable."

    async def _prepare_monthly_agenda(self, user_id: str, tenant_id: str) -> str:
        context = await self._build_monthly_context(user_id)
        try:
            return await self.ai.complete(
                system=_MONTHLY_AI_SYSTEM,
                user=f"Monthly context:\n{json.dumps(context, ensure_ascii=False, indent=2)}",
                tier=3,  # Strategic tier for monthly
            )
        except Exception:
            return "Monthly analysis unavailable."

    async def _build_daily_context(self, user_id: str) -> dict:
        from datetime import date
        from sqlalchemy import select as sel
        from app.models.energy_score import EnergyScore
        from app.models.day_plan import DayPlan

        energy_q = (
            sel(EnergyScore)
            .where(EnergyScore.user_id == user_id)
            .order_by(EnergyScore.created_at.desc())
            .limit(1)
        )
        energy = (await self.db.execute(energy_q)).scalar_one_or_none()

        plan_q = (
            sel(DayPlan)
            .where(DayPlan.user_id == user_id, DayPlan.plan_date == date.today())
            .limit(1)
        )
        plan = (await self.db.execute(plan_q)).scalar_one_or_none()

        return {
            "energy_state": energy.state if energy else "unknown",
            "energy_score": energy.score if energy else None,
            "plan_items": plan.items[:10] if plan and plan.items else [],
            "date": date.today().isoformat(),
        }

    async def _build_weekly_context(self, user_id: str) -> dict:
        from datetime import date, timedelta
        from sqlalchemy import select as sel, func
        from app.models.day_plan import DayPlan

        week_ago = date.today() - timedelta(days=7)
        plans_q = sel(DayPlan).where(
            DayPlan.user_id == user_id,
            DayPlan.plan_date >= week_ago,
        )
        plans = (await self.db.execute(plans_q)).scalars().all()
        total_items = sum(len(p.items or []) for p in plans)
        accepted = sum(1 for p in plans if p.status in ("accepted", "completed"))

        return {
            "plans_this_week": len(plans),
            "plans_accepted": accepted,
            "total_tasks_planned": total_items,
        }

    async def _build_monthly_context(self, user_id: str) -> dict:
        from datetime import date, timedelta
        from sqlalchemy import select as sel
        from app.models.planning_goal import PlanningGoal

        goals_q = sel(PlanningGoal).where(
            PlanningGoal.user_id == user_id,
            PlanningGoal.status == "active",
        )
        goals = (await self.db.execute(goals_q)).scalars().all()

        return {
            "active_goals": [
                {"title": g.title, "horizon": g.horizon, "id": str(g.id)}
                for g in goals
            ],
        }

    async def _update_strategic_kernel(
        self,
        user_id: str,
        tenant_id: str,
        session: ReviewSession,
        answers: dict,
    ) -> None:
        """Deactivate old kernel, create new one from review answers."""
        from sqlalchemy import update as upd
        await self.db.execute(
            upd(StrategicKernel)
            .where(
                StrategicKernel.user_id == user_id,
                StrategicKernel.is_active == True,  # noqa: E712
            )
            .values(is_active=False)
        )

        # Build new kernel context text for AI injection
        context_text = _build_strategic_context(answers, session.review_type)

        existing_q = (
            select(StrategicKernel)
            .where(StrategicKernel.user_id == user_id)
            .order_by(StrategicKernel.version.desc())
            .limit(1)
        )
        last = (await self.db.execute(existing_q)).scalar_one_or_none()
        next_version = (last.version + 1) if last else 1

        new_kernel = StrategicKernel(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            user_id=uuid.UUID(user_id),
            version=next_version,
            is_active=True,
            review_type=session.review_type,
            weekly_focus=_extract_weekly_focus(answers),
            not_now=_extract_not_now(answers),
            strategic_context_for_ai=context_text,
        )
        self.db.add(new_kernel)
        await self.db.flush()


def _extract_weekly_focus(answers: dict) -> list:
    raw = answers.get("w3", "")
    if not raw:
        return []
    return [{"title": line.strip()} for line in raw.split("\n") if line.strip()][:3]


def _extract_not_now(answers: dict) -> list:
    raw = answers.get("w4", "") or answers.get("m5", "")
    if not raw:
        return []
    return [{"title": line.strip(), "reason": "User decision"} for line in raw.split("\n") if line.strip()]


def _build_strategic_context(answers: dict, review_type: str) -> str:
    parts = [f"Strategic kernel from {review_type} review."]
    for key, val in answers.items():
        if val:
            parts.append(f"- {key}: {val}")
    return "\n".join(parts)


_DEFAULT_DAILY_QUESTIONS = [
    {"id": "d1", "text": "Что самое важное сегодня?", "answer_type": "text", "required": True},
    {"id": "d3", "text": "Подтверди план дня", "answer_type": "confirm_plan", "required": True},
]

_DAILY_AI_SYSTEM = """Ты исполнительный ассистент. Твоя задача — подготовить утреннюю планёрку.

Ответь в JSON:
{
  "agenda": "<2-4 предложения: ключевые риски и фокус дня>",
  "plan": [
    {"step_id": "<id или null>", "title": "<название задачи>", "estimated_minutes": <число>, "reason": "<почему именно сейчас>"},
    ...
  ]
}

Правила:
- Максимум 7 задач в плане
- Сначала срочное, потом важное
- Учитывай энергию пользователя
- Отвечай на языке пользователя (русский)
- Будь конкретным и прямым"""

_WEEKLY_AI_SYSTEM = """Ты исполнительный ассистент. Подготовь еженедельный обзор.
Будь честным и прямым. 3-5 предложений.
Отвечай на русском языке."""

_MONTHLY_AI_SYSTEM = """Ты стратегический советник. Подготовь ежемесячный стратегический анализ.
Оцени прогресс по целям, выяви паттерны, дай чёткие рекомендации по корректировке.
Отвечай на русском языке. 5-7 предложений."""
