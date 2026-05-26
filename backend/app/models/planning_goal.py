import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class PlanningGoal(AuditedModel):
    """
    A goal at a specific planning horizon.
    horizon: vision | annual | quarterly | monthly | weekly | daily
    status: active | completed | abandoned  (non-FSM, validated in API layer)
    parent_id: optional soft-ref to parent PlanningGoal (hierarchy validation in service)
    """

    __tablename__ = "planning_goals"

    horizon: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
