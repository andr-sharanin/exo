"""Repository for OnboardingSession — inherits BaseRepository for standard CRUD."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.onboarding_session import OnboardingSession
from app.repositories.base import BaseRepository


class OnboardingSessionRepo(BaseRepository[OnboardingSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OnboardingSession, session)

    async def get_latest_completed(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> OnboardingSession | None:
        result = await self._session.execute(
            select(OnboardingSession)
            .where(
                OnboardingSession.tenant_id == tenant_id,
                OnboardingSession.user_id == user_id,
                OnboardingSession.status == "completed",
            )
            .order_by(OnboardingSession.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
