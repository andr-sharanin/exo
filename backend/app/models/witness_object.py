import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import WitnessStatus


class WitnessObject(AuditedModel):
    """
    Verification record for a completed Step.
    Hierarchy: passive → linked → manual.
    Manual witness cannot produce 'verified' — only 'reported' or 'partial'.
    OutcomeObject.outcome_type=done requires verified witness.
    """

    __tablename__ = "witness_objects"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=WitnessStatus.PENDING, index=True
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    execution_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    witness_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="passive | linked | manual"
    )
    witness_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verification_class: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="verified | reported | partial — manual can only produce reported/partial"
    )
    evidence_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Screenshot URI, system log reference, or other proof"
    )
