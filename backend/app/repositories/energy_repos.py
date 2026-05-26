"""Repositories for Phase 4: EnergyScore, SystemMode, ClientKernelProfile, signal queries."""
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavioral_event import BehavioralEvent
from app.models.client_kernel_profile import ClientKernelProfile
from app.models.energy_score import EnergyScore
from app.models.execution_session import ExecutionSession
from app.models.system_mode import SystemMode
from app.services.fsm import SessionStatus


class EnergyScoreRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> EnergyScore | None:
        result = await self._session.execute(
            select(EnergyScore)
            .where(EnergyScore.tenant_id == tenant_id, EnergyScore.user_id == user_id)
            .order_by(EnergyScore.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, score: EnergyScore) -> EnergyScore:
        self._session.add(score)
        await self._session.flush()
        await self._session.refresh(score)
        return score


class SystemModeRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> SystemMode | None:
        result = await self._session.execute(
            select(SystemMode)
            .where(SystemMode.tenant_id == tenant_id, SystemMode.user_id == user_id)
            .order_by(SystemMode.switched_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, mode: SystemMode) -> SystemMode:
        self._session.add(mode)
        await self._session.flush()
        await self._session.refresh(mode)
        return mode


class ClientKernelProfileRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> ClientKernelProfile | None:
        result = await self._session.execute(
            select(ClientKernelProfile)
            .where(
                ClientKernelProfile.tenant_id == tenant_id,
                ClientKernelProfile.user_id == user_id,
            )
            .order_by(ClientKernelProfile.calibrated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, profile: ClientKernelProfile) -> ClientKernelProfile:
        self._session.add(profile)
        await self._session.flush()
        await self._session.refresh(profile)
        return profile


class EnergyDataRepo:
    """Indirect signal query helpers — feeds EnergyScoreEngine.apply_indirect_signals()."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_abandoned_sessions_since(
        self, tenant_id: uuid.UUID, since: datetime
    ) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ExecutionSession)
            .where(
                ExecutionSession.tenant_id == tenant_id,
                ExecutionSession.status == SessionStatus.ABANDONED,
                ExecutionSession.created_at >= since,
            )
        )
        return result.scalar_one()

    async def count_events_by_type_since(
        self, tenant_id: uuid.UUID, event_type: str, since: datetime
    ) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(BehavioralEvent)
            .where(
                BehavioralEvent.tenant_id == tenant_id,
                BehavioralEvent.behavioral_event_type == event_type,
                BehavioralEvent.event_timestamp >= since,
            )
        )
        return result.scalar_one()
