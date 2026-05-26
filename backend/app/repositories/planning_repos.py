import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning_goal import PlanningGoal
from app.repositories.base import BaseRepository


class PlanningGoalRepo(BaseRepository[PlanningGoal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PlanningGoal, session)

    async def list_by_horizon(
        self, tenant_id: uuid.UUID, horizon: str
    ) -> list[PlanningGoal]:
        result = await self._session.execute(
            select(PlanningGoal)
            .where(
                PlanningGoal.tenant_id == tenant_id,
                PlanningGoal.horizon == horizon,
            )
            .order_by(PlanningGoal.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_parent_horizon(
        self, parent_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> str | None:
        result = await self._session.execute(
            select(PlanningGoal.horizon).where(
                PlanningGoal.id == parent_id,
                PlanningGoal.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return row
