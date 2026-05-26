import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SensitivityClass(StrEnum):
    STANDARD = "standard"
    PRIVATE = "private"
    HIGH_SENSITIVE = "high_sensitive"


class AuditedModel(Base):
    """
    Common field envelope for all 12 canonical ExoCortex objects.

    Every canonical object MUST inherit from this class.
    Fields are immutable after creation except updated_at and schema_version.
    Tenant isolation is enforced at DB level via Row Level Security (Phase 1).
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant isolation key — RLS enforced at DB level",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Incremented on structural field additions for forward-compatibility",
    )
    sensitivity_class: Mapped[str] = mapped_column(
        String(32),
        default=SensitivityClass.STANDARD,
        nullable=False,
        comment="BehavioralEvent always HIGH_SENSITIVE; enforced in model validators",
    )
