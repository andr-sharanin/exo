from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class EnergyScore(AuditedModel):
    """
    Point-in-time energy measurement created by check-in or manual override.
    `state` is the hysteresis-stabilised level; `score` is the raw 0–100 value.
    No `status` column — EnergyScore is immutable after creation (append-only log).
    """

    __tablename__ = "energy_scores"

    score: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="sufficient | constrained | critical — hysteresis-stabilised",
    )
    checkin_signals: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Raw check-in inputs: sleep_quality, mood, energy_level, note",
    )
    indirect_signals: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Computed indirect signals snapshot: abandoned_sessions, urge_events_6h, etc.",
    )
    is_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True = manual override bypassed check-in computation",
    )
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Score validity window — triggers re-check-in nudge when expired",
    )
