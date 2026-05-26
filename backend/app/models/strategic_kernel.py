from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class StrategicKernel(AuditedModel):
    """
    Strategic kernel — the user's current goal landscape.
    Rebuilt/updated after each review session (daily/weekly/monthly).

    Used alongside PolicyKernel to analyze whether a new task
    aligns with the user's direction RIGHT NOW.
    """

    __tablename__ = "strategic_kernels"

    # Current active focus areas (from planning_goals, distilled per review)
    vision_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="One-sentence life vision"
    )
    annual_priorities: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="List of {title, goal_id} for current year"
    )
    quarterly_okrs: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="List of {objective, key_results[], goal_id}"
    )
    weekly_focus: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="List of {title, why, goal_id} — this week's 3 priorities"
    )

    # What the user explicitly decided NOT to do right now
    not_now: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="Tasks/projects deliberately deferred: [{title, reason, revisit_date}]"
    )

    # AI-generated strategic context for task analysis prompts
    strategic_context_for_ai: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Pre-computed text summary injected into task analysis prompts"
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    review_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="weekly",
        comment="daily|weekly|monthly — which review produced this kernel"
    )
