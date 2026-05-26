import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment_deposit import CommitmentDeposit
from app.repositories.base import BaseRepository


class CommitmentDepositRepo(BaseRepository[CommitmentDeposit]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CommitmentDeposit, session)

    async def list_by_user(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[CommitmentDeposit]:
        result = await self._session.execute(
            select(CommitmentDeposit)
            .where(
                CommitmentDeposit.tenant_id == tenant_id,
                CommitmentDeposit.user_id == user_id,
            )
            .order_by(CommitmentDeposit.created_at.desc())
        )
        return list(result.scalars().all())
