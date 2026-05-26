import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GovernanceSetting(Base):
    """Per-user governance mode: solo (self-confirm) or x2 (partner must approve)."""
    __tablename__ = "governance_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="solo",
                                       comment="solo | x2")
    partner_email: Mapped[str | None] = mapped_column(String(320), nullable=True,
                                                        comment="Required when mode=x2")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                   onupdate=func.now())


class GovernanceRecord(Base):
    """Architecture Decision Record — written justification for a reversal or deferral."""
    __tablename__ = "governance_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    subject: Mapped[str] = mapped_column(String(512), nullable=False,
                                          comment="What decision is being reversed/deferred")
    reason: Mapped[str] = mapped_column(Text, nullable=False,
                                         comment="Written justification (min 20 chars enforced at API level)")
    mode_at_time: Mapped[str] = mapped_column(String(16), nullable=False,
                                               comment="solo | x2 — captured at creation time")

    # x2 approval
    partner_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    approval_token: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="self_approved",
                                         comment="self_approved | pending_partner | partner_approved")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
