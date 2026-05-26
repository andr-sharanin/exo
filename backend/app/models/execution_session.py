import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import SessionStatus


class ExecutionSession(AuditedModel):
    """
    Active work session on a single Step.
    Feeds LifeWorm timer data — actual_duration_minutes written on complete/abandon.
    Energy gating happens before session creation: critical energy blocks new sessions.
    """

    __tablename__ = "execution_sessions"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SessionStatus.ACTIVE, index=True
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    session_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    session_ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_mode: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="focus | background | rescue"
    )
    actual_duration_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Written on completion or abandonment"
    )
