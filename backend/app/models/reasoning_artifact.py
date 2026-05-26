import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import ReasoningStatus


class ReasoningArtifact(AuditedModel):
    """
    AI-assisted analysis of a CaptureRecord.
    Skipped for nano_task and fast_track flows (status=skipped).
    reasoning_model_role records which AI tier produced this artifact.
    """

    __tablename__ = "reasoning_artifacts"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ReasoningStatus.PENDING, index=True
    )
    capture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    reasoning_stage: Mapped[str] = mapped_column(
        String(8), nullable=False,
        comment="L0=quick | L1=structured | L2=analytical | L3=deep"
    )
    intent_hypothesis: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="AI-generated interpretation of user intent"
    )
    ambiguity_level: Mapped[str] = mapped_column(
        String(16), nullable=False,
        comment="none | low | medium | high"
    )
    actionability_status: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="actionable | needs_clarification | non_actionable | defer_candidate"
    )
    reasoning_model_role: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="AI tier and model that produced this artifact"
    )
