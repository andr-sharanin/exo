import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_message import AgentMessage
from app.repositories.base import BaseRepository


class AgentMessageRepo(BaseRepository[AgentMessage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AgentMessage, session)

    async def get_by_session(self, session_id: uuid.UUID) -> list[AgentMessage]:
        result = await self._session.execute(
            select(AgentMessage)
            .where(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.message_order.asc())
        )
        return list(result.scalars().all())

    async def count_by_session(self, session_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(AgentMessage).where(AgentMessage.session_id == session_id)
        )
        return len(result.scalars().all())
