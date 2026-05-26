import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class ReviewSession(AuditedModel):
    """
    An instance of a планёрка for a specific user.
    Created automatically by ARQ scheduler or manually by user.

    Daily  → created each morning → user confirms plan → executes all day without thinking
    Weekly → Friday evening → review week → update weekly_focus in StrategicKernel
    Monthly → last day of month → strategic recalibration → rebuild StrategicKernel
    """

    __tablename__ = "review_sessions"

    review_type: Mapped[str] = mapped_column(
        String(16), nullable=False,
        comment="daily|weekly|monthly"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending",
        comment="pending|in_progress|completed|skipped"
    )

    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="ReviewTemplate used (snapshot taken at creation)"
    )
    questions_snapshot: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="Copy of template questions at creation time (template may change)"
    )

    # AI-prepared agenda (generated before user opens the session)
    ai_agenda: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="AI-generated briefing: what happened, what's at risk, recommended focus"
    )
    ai_plan_suggestion: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="For daily: AI-suggested ordered task list [{step_id, title, estimated_minutes, reason}]"
    )

    # User responses
    answers: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="question_id → answer"
    )
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Outcomes
    plan_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Daily: did user confirm the AI plan?"
    )
    plan_adjustments: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="Daily: user-requested changes to AI plan"
    )
    goals_updated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Weekly/monthly: were goals/kernel updated as result?"
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
