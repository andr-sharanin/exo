"""
Generic async repository. All canonical object repositories inherit from this.
"""
import uuid
from typing import Generic, TypeVar, Type

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import AuditedModel

T = TypeVar("T", bound=AuditedModel)


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get(self, id: uuid.UUID, tenant_id: uuid.UUID) -> T | None:
        result = await self._session.execute(
            select(self._model).where(
                self._model.id == id,
                self._model.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_404(self, id: uuid.UUID, tenant_id: uuid.UUID) -> T:
        from fastapi import HTTPException, status
        obj = await self.get(id, tenant_id)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self._model.__name__} {id} not found",
            )
        return obj

    async def create(self, obj: T) -> T:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[T]:
        q = select(self._model).where(self._model.tenant_id == tenant_id)
        if status:
            q = q.where(self._model.status == status)
        q = q.order_by(self._model.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def count_by_tenant(
        self, tenant_id: uuid.UUID, *, status: str | None = None
    ) -> int:
        q = select(func.count()).select_from(self._model).where(
            self._model.tenant_id == tenant_id
        )
        if status:
            q = q.where(self._model.status == status)
        result = await self._session.execute(q)
        return result.scalar_one()
