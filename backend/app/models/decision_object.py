import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import DecisionStatus


class DecisionObject(AuditedModel):
    """
    Human-confirmed decision about what to do with a captured intent.
    confirmed_by_user=True is required before status→confirmed.
    fast_track_record must be populated when decision_outcome=fast_track.
    """

    __tablename__ = "decision_objects"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DecisionStatus.PENDING, index=True
    )
    capture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    reasoning_ref: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="Null for nano_task or fast_track — reasoning was skipped"
    )
    decision_outcome: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="accept | defer | reject | clarify | decision_support | fast_track"
    )
    confirmed_by_user: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Human confirmation required — kernel cannot auto-confirm"
    )
    decision_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fast_track_record: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Required when decision_outcome=fast_track: {rationale, acknowledged_risk, skipped_reasoning, time_pressure}"
    )
