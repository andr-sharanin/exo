import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class HabitDefinition(AuditedModel):
    """User-defined habit to track daily/weekly."""

    __tablename__ = "habit_definitions"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency: Mapped[str] = mapped_column(
        String(32), nullable=False, default="daily",
        comment="daily|weekdays|weekly|custom"
    )
    target_days: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="For custom frequency: [0,1,2,3,4] = Mon-Fri (0=Monday)"
    )
    target_time: Mapped[str | None] = mapped_column(
        String(8), nullable=True,
        comment="HH:MM preferred completion time"
    )
    estimated_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10
    )
    category: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="health|learning|mindfulness|productivity|social|custom"
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="Optional link to a planning_goal"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Secretary can include habit in daily plan automatically
    include_in_plan: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


class HabitEntry(AuditedModel):
    """
    Single habit completion record. Append-only — never updated.
    Idempotent per (habit_id, date): service rejects duplicate same-day entries.
    """

    __tablename__ = "habit_entries"

    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quality: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Optional self-rating 1-5"
    )
