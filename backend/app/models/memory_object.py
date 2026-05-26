import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import MemoryStatus


class MemoryObject(AuditedModel):
    """
    Persistent contextual memory extracted from user behavior and pipeline events.
    Used by AI entities to maintain continuity across sessions.
    relevance_score is updated by the Learning stage of the pipeline.
    """

    __tablename__ = "memory_objects"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MemoryStatus.ACTIVE, index=True
    )
    memory_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="pattern | preference | fact | context"
    )
    content_ref: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Stored memory content or external storage reference"
    )
    relevance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
        comment="0.0-1.0; updated by Learning stage"
    )
    source_object_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="Canonical object type that generated this memory"
    )
    source_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
