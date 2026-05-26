import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class OutcomeObject(AuditedModel):
    """
    Terminal record of a Step's final state.
    OutcomeObject IS the terminal state — it has no status field.
    outcome_type=completed requires a WitnessObject with verification_class=verified.
    This object is immutable after creation.
    """

    __tablename__ = "outcome_objects"

    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    witness_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    outcome_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="completed | partially_completed | interrupted | cancelled | expired | failed_verification"
    )
    outcome_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
