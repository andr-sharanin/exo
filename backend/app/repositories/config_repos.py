from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig
from app.models.push_subscription import PushSubscription
from app.repositories.base import BaseRepository


class SystemConfigRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> list[SystemConfig]:
        result = await self._session.execute(
            select(SystemConfig).order_by(SystemConfig.category, SystemConfig.key)
        )
        return list(result.scalars().all())

    async def get_by_key(self, key: str) -> SystemConfig | None:
        result = await self._session.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        return result.scalar_one_or_none()

    async def upsert(self, entry: SystemConfig) -> SystemConfig:
        existing = await self.get_by_key(entry.key)
        if existing:
            existing.value = entry.value
            existing.is_secret = entry.is_secret
            existing.description = entry.description
            existing.category = entry.category
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry


class PushSubscriptionRepo(BaseRepository[PushSubscription]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PushSubscription, session)
