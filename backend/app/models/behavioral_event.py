from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel, SensitivityClass
from app.services.fsm import BehavioralEventStatus


class BehavioralEvent(AuditedModel):
    """
    High-sensitivity record of behavioral patterns: urges, lapses, recovery, risk windows.
    sensitivity_class is ALWAYS high_sensitive — enforced in __init__, cannot be overridden.
    These events feed the Behavioral Policy engine and never leave the user's private context.
    """

    __tablename__ = "behavioral_events"

    def __init__(self, **kwargs) -> None:
        kwargs["sensitivity_class"] = SensitivityClass.HIGH_SENSITIVE
        super().__init__(**kwargs)

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=BehavioralEventStatus.RECORDED, index=True
    )
    behavioral_event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="urge_event | lapse_event | recovery_event | risk_window"
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    user_declared_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="True=user declared; False=system inferred from behavioral patterns"
    )
    trigger_description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="User-provided description of trigger — stored encrypted in high_sensitive context"
    )
    context_ref: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="References to related pipeline objects (step_id, session_id, etc.)"
    )
