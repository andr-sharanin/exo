import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import EntitySessionStatus


class EntitySession(AuditedModel):
    """
    A bounded advisory interaction with an AI entity.
    Entities are advisory-only — they CANNOT mutate canonical pipeline objects.
    context_ref stores references to relevant canonical objects for this session.
    """

    __tablename__ = "entity_sessions"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EntitySessionStatus.ACTIVE, index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="core_advisor | tutor | reflective_support | coach | consultant"
    )
    session_mode: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="advisory | reflection | planning"
    )
    context_ref: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="References to relevant canonical object IDs providing session context"
    )
    session_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    session_ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
