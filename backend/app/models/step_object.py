import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import StepStatus


class StepObject(AuditedModel):
    """
    Atomic executable unit decomposed from a Decision.
    One Decision may have multiple Steps (ordered by step_order).
    LifeWorm executes one Step at a time.
    """

    __tablename__ = "step_objects"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=StepStatus.PENDING, index=True
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    step_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="focus_step | background_step | rescue_entry_step"
    )
    execution_readiness: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="ready | blocked | needs_clarification"
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    definition_of_done_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Criteria text or external reference — what 'done' looks like"
    )
    step_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="Position within the parent task execution sequence"
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
