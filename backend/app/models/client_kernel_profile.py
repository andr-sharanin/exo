from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class ClientKernelProfile(AuditedModel):
    """
    Behavioural calibration profile produced by onboarding (Phase 5).
    Stored here in Phase 4 so energy and mode layers can reference the schema.
    Used by Secretary (Phase 7) and AI Router (Phase 6) to personalise recommendations.
    Versioned: each re-calibration appends a new record.
    """

    __tablename__ = "client_kernel_profiles"

    calibration_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    calibrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    profile_data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment=(
            "Onboarding results: focus_stability, task_handling_style, decision_style, "
            "overload_threshold, interruption_behavior, clarity_strategy, "
            "execution_pattern, help_seeking_behavior, failure_response_pattern"
        ),
    )
    computed_defaults: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment="Derived fields: dominant_mode, energy_archetype, recommended_session_length",
    )
