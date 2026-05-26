import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class PolicyKernel(AuditedModel):
    """
    Behavioral policy kernel — formed from deep onboarding interview.
    Describes HOW the user thinks, decides, and works.
    Used to filter/analyze tasks before they enter the execution pipeline.

    append-only: each recalibration creates a new record (version++).
    Active kernel: is_active=True (only one per user at a time, enforced in service).
    """

    __tablename__ = "policy_kernels"

    # Structured behavioral dimensions (derived from onboarding answers)
    focus_stability: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="high|medium|low — how long user sustains focus"
    )
    task_handling_style: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="sequential|parallel|burst"
    )
    decision_style: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="deliberate|fast|collaborative"
    )
    overload_threshold: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="low|medium|high — how many tasks before cognitive overload"
    )
    interruption_behavior: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="absorb|context_switch|reject"
    )
    clarity_strategy: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="writing|talking|thinking|doing"
    )
    execution_pattern: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="planned|reactive|deadline_driven"
    )
    help_seeking_behavior: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="proactive|reactive|avoidant"
    )
    failure_response_pattern: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="redirect|freeze|push_through|seek_support"
    )
    dominant_mode: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="harmony|achiever|recovery|creative|learning|clarity|crisis"
    )

    # Raw answers and AI-derived insights (for context in AI prompts)
    raw_answers: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Original onboarding answers keyed by question_id"
    )
    ai_insights: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="AI-extracted behavioral patterns and recommendations"
    )
    constraints: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="List of behavioral constraints: things this user should NOT do"
    )
    strengths: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="List of behavioral strengths to leverage"
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    calibration_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="onboarding",
        comment="onboarding|recalibration|behavioral_data"
    )
