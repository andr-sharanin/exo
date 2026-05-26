import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class OnboardingSessionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class OnboardingSession(AuditedModel):
    """
    Tracks a single onboarding calibration run.
    Append-only: each re-calibration creates a new session.
    status transitions: in_progress → completed (validated in API layer).
    """

    __tablename__ = "onboarding_sessions"

    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=OnboardingSessionStatus.IN_PROGRESS, index=True
    )
    answers: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="{question_id: option_id} — populated on submit",
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Soft reference to client_kernel_profiles.id set on completion",
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
