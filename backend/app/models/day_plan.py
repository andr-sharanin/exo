import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class DayPlan(AuditedModel):
    """
    AI-generated daily execution plan.
    status: draft → accepted → completed (validated in API layer, not FSM).
    items: JSON list of scored StepObject references.
    """

    __tablename__ = "day_plans"

    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True
    )
    items: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    energy_state_at_generation: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    system_mode_at_generation: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    total_estimated_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
