import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class TaskAnalysis(AuditedModel):
    """
    Result of KernelFilterService analysis for a command.
    One record per command (re-analysis creates new record).
    """

    __tablename__ = "task_analyses"

    command_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    alignment_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflicts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    synergies: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confirm_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suggested_timing: Mapped[str | None] = mapped_column(String(32), nullable=True)
    defer_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_decision: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="confirmed|deferred|overridden"
    )
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
