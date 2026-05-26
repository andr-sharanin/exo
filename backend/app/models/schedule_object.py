import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import ScheduleStatus


class ScheduleObject(AuditedModel):
    """
    Temporal placement of a confirmed decision.
    schedule_authority_type records who placed this in the schedule:
    user (manual), secretary (AI agent), or system (auto-schedule rule).
    """

    __tablename__ = "schedule_objects"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ScheduleStatus.PENDING, index=True
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    schedule_mode: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="schedule_now | manual_schedule | auto_schedule"
    )
    scheduled_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    scheduled_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    schedule_authority_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="user | secretary | system"
    )
