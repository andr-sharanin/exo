import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.day_plan import DayPlan
from app.repositories.base import BaseRepository


class DayPlanRepo(BaseRepository[DayPlan]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DayPlan, session)

    async def get_today_for_tenant(self, tenant_id: uuid.UUID) -> DayPlan | None:
        result = await self._session.execute(
            select(DayPlan)
            .where(
                DayPlan.tenant_id == tenant_id,
                DayPlan.plan_date == date.today(),
            )
            .order_by(DayPlan.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
