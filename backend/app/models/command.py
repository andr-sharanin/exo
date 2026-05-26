import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import CommandStatus


class Command(AuditedModel):
    """
    Pipeline entry point. Every user intent enters as a Command.
    Immutable after creation except status transitions via FSM.
    """

    __tablename__ = "commands"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_command_idempotency"),
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CommandStatus.PENDING, index=True
    )
    ingress_channel: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="web | mobile | telegram | api | voice"
    )
    ingress_modality: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="text | voice | quick_capture | structured"
    )
    raw_payload_ref: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Raw input text or storage reference URI"
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="Client-generated key; unique per tenant"
    )
    raw_input: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Human-readable text for kernel analysis (extracted from raw_payload_ref)"
    )
    kernel_status: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True,
        comment="null|pending_analysis|pending_confirmation|confirmed|deferred"
    )
