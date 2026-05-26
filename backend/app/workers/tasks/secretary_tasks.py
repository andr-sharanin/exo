"""Background task: generate day plan."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select


async def generate_plan_task(ctx: dict, tenant_id: str, user_id: str) -> dict:
    """
    ARQ task: build a DayPlan for tenant_id/user_id and publish SSE event.

    Fetches real energy state and system mode from DB.
    Includes habits with include_in_plan=True (not yet done today) as background items.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.day_plan import DayPlan
    from app.models.habit import HabitDefinition, HabitEntry
    from app.repositories.energy_repos import EnergyScoreRepo, SystemModeRepo
    from app.repositories.pipeline_repos import StepObjectRepo
    from app.repositories.secretary_repos import DayPlanRepo
    from app.services.event_publisher import publish
    from app.services.secretary import SecretaryService

    t_id = uuid.UUID(tenant_id)
    u_id = uuid.UUID(user_id)

    db_factory = ctx.get("db_factory", AsyncSessionLocal)
    async with db_factory() as db:
        try:
            # ── Real energy state ────────────────────────────────────────────
            energy_rec = await EnergyScoreRepo(db).get_latest(t_id, u_id)
            energy_state = energy_rec.state if energy_rec else "sufficient"

            # ── Real system mode ─────────────────────────────────────────────
            mode_rec = await SystemModeRepo(db).get_current(t_id, u_id)
            system_mode = mode_rec.mode if mode_rec else "harmony"

            # ── Pipeline steps ───────────────────────────────────────────────
            steps_raw = await StepObjectRepo(db).list_by_tenant(t_id)
            step_dicts = [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "step_type": s.step_type,
                    "execution_readiness": s.execution_readiness,
                    "estimated_minutes": s.estimated_minutes,
                }
                for s in steps_raw
            ]

            # ── Habits to include in plan ────────────────────────────────────
            today = date.today()
            habits_q = select(HabitDefinition).where(
                HabitDefinition.user_id == u_id,
                HabitDefinition.is_active == True,  # noqa: E712
                HabitDefinition.include_in_plan == True,  # noqa: E712
            )
            habits = list((await db.execute(habits_q)).scalars().all())

            # Filter out habits already checked in today
            habit_dicts = []
            for h in habits:
                done_q = select(HabitEntry).where(
                    HabitEntry.habit_id == h.id,
                    func.date(HabitEntry.completed_at) == today,
                )
                if (await db.execute(done_q)).scalar_one_or_none():
                    continue
                habit_dicts.append({
                    "id": f"habit:{h.id}",
                    "title": h.title,
                    "step_type": "background_step",
                    "execution_readiness": "ready",
                    "estimated_minutes": h.estimated_minutes,
                    "_is_habit": True,
                })

            items = SecretaryService.build_plan(
                step_dicts + habit_dicts, energy_state, system_mode
            )
            total = SecretaryService.total_minutes(items)

            plan = await DayPlanRepo(db).create(
                DayPlan(
                    id=uuid.uuid4(),
                    tenant_id=t_id,
                    user_id=u_id,
                    plan_date=today,
                    status="draft",
                    items=items,
                    energy_state_at_generation=energy_state,
                    system_mode_at_generation=system_mode,
                    total_estimated_minutes=total,
                    generated_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()

            await publish(user_id, "plan_ready", {"plan_id": str(plan.id)})
            return {"plan_id": str(plan.id), "status": "done"}

        except Exception as exc:
            await publish(user_id, "job_failed", {"job": "generate_plan", "error": str(exc)})
            raise
