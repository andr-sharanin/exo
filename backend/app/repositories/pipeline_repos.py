"""
Thin repositories for all 12 canonical objects.
Each adds parent-scoped queries on top of BaseRepository.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.command import Command
from app.services.fsm import SessionStatus
from app.models.capture_record import CaptureRecord
from app.models.reasoning_artifact import ReasoningArtifact
from app.models.decision_object import DecisionObject
from app.models.schedule_object import ScheduleObject
from app.models.step_object import StepObject
from app.models.execution_session import ExecutionSession
from app.models.witness_object import WitnessObject
from app.models.outcome_object import OutcomeObject
from app.models.entity_session import EntitySession
from app.models.memory_object import MemoryObject
from app.models.behavioral_event import BehavioralEvent


class CommandRepo(BaseRepository[Command]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Command, session)

    async def get_by_idempotency_key(
        self, tenant_id: uuid.UUID, key: str
    ) -> Command | None:
        result = await self._session.execute(
            select(Command).where(
                Command.tenant_id == tenant_id,
                Command.idempotency_key == key,
            )
        )
        return result.scalar_one_or_none()


class CaptureRecordRepo(BaseRepository[CaptureRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CaptureRecord, session)

    async def get_by_command(
        self, command_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CaptureRecord | None:
        result = await self._session.execute(
            select(CaptureRecord).where(
                CaptureRecord.command_id == command_id,
                CaptureRecord.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()


class ReasoningArtifactRepo(BaseRepository[ReasoningArtifact]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ReasoningArtifact, session)

    async def get_by_capture(
        self, capture_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ReasoningArtifact | None:
        result = await self._session.execute(
            select(ReasoningArtifact).where(
                ReasoningArtifact.capture_id == capture_id,
                ReasoningArtifact.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()


class DecisionObjectRepo(BaseRepository[DecisionObject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DecisionObject, session)

    async def get_by_capture(
        self, capture_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DecisionObject | None:
        result = await self._session.execute(
            select(DecisionObject).where(
                DecisionObject.capture_id == capture_id,
                DecisionObject.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()


class ScheduleObjectRepo(BaseRepository[ScheduleObject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ScheduleObject, session)

    async def get_by_decision(
        self, decision_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ScheduleObject | None:
        result = await self._session.execute(
            select(ScheduleObject).where(
                ScheduleObject.decision_id == decision_id,
                ScheduleObject.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()


class StepObjectRepo(BaseRepository[StepObject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StepObject, session)

    async def list_by_decision(
        self, decision_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[StepObject]:
        result = await self._session.execute(
            select(StepObject)
            .where(
                StepObject.decision_id == decision_id,
                StepObject.tenant_id == tenant_id,
            )
            .order_by(StepObject.step_order)
        )
        return list(result.scalars().all())

    async def list_active_for_user(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[StepObject]:
        """Return all non-terminal steps for a user (pending/ready/in_progress)."""
        result = await self._session.execute(
            select(StepObject)
            .where(
                StepObject.tenant_id == tenant_id,
                StepObject.user_id == user_id,
                StepObject.status.in_(["pending", "ready", "in_progress"]),
            )
            .order_by(StepObject.created_at.desc())
            .limit(100)
        )
        return list(result.scalars().all())

    async def list_quick_wins(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, max_minutes: int = 15
    ) -> list[StepObject]:
        """Return ready/pending steps with estimated_minutes <= max_minutes."""
        from sqlalchemy import or_
        result = await self._session.execute(
            select(StepObject)
            .where(
                StepObject.tenant_id == tenant_id,
                StepObject.user_id == user_id,
                StepObject.status.in_(["pending", "ready"]),
                StepObject.execution_readiness == "ready",
                or_(
                    StepObject.estimated_minutes == None,  # noqa: E711
                    StepObject.estimated_minutes <= max_minutes,
                ),
            )
            .order_by(StepObject.created_at)
        )
        return list(result.scalars().all())


class ExecutionSessionRepo(BaseRepository[ExecutionSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExecutionSession, session)

    async def get_active_for_step(
        self, step_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ExecutionSession | None:
        result = await self._session.execute(
            select(ExecutionSession).where(
                ExecutionSession.step_id == step_id,
                ExecutionSession.tenant_id == tenant_id,
                ExecutionSession.status == SessionStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()


class WitnessObjectRepo(BaseRepository[WitnessObject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WitnessObject, session)

    async def get_by_step(
        self, step_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> WitnessObject | None:
        result = await self._session.execute(
            select(WitnessObject).where(
                WitnessObject.step_id == step_id,
                WitnessObject.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()


class OutcomeObjectRepo(BaseRepository[OutcomeObject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OutcomeObject, session)  # type: ignore[arg-type]

    async def list_by_tenant(  # type: ignore[override]
        self,
        tenant_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OutcomeObject]:
        # OutcomeObject has no status column — status param intentionally ignored
        q = (
            select(OutcomeObject)
            .where(OutcomeObject.tenant_id == tenant_id)
            .order_by(OutcomeObject.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def count_by_tenant(  # type: ignore[override]
        self, tenant_id: uuid.UUID, *, status: str | None = None
    ) -> int:
        from sqlalchemy import func as sa_func
        result = await self._session.execute(
            select(sa_func.count()).select_from(OutcomeObject).where(
                OutcomeObject.tenant_id == tenant_id
            )
        )
        return result.scalar_one()

    async def get_by_step(
        self, step_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> OutcomeObject | None:
        result = await self._session.execute(
            select(OutcomeObject).where(
                OutcomeObject.step_id == step_id,
                OutcomeObject.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()


class EntitySessionRepo(BaseRepository[EntitySession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EntitySession, session)


class MemoryObjectRepo(BaseRepository[MemoryObject]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MemoryObject, session)


class BehavioralEventRepo(BaseRepository[BehavioralEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BehavioralEvent, session)

    async def list_by_type(
        self,
        tenant_id: uuid.UUID,
        event_type: str,
        limit: int = 50,
    ) -> list[BehavioralEvent]:
        result = await self._session.execute(
            select(BehavioralEvent)
            .where(
                BehavioralEvent.tenant_id == tenant_id,
                BehavioralEvent.behavioral_event_type == event_type,
            )
            .order_by(BehavioralEvent.event_timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
