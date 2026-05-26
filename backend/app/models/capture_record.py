import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel
from app.services.fsm import CaptureStatus


class CaptureRecord(AuditedModel):
    """
    Verified snapshot of a Command's raw payload.
    capture_hash ensures payload integrity — mismatch sets integrity_failed.
    """

    __tablename__ = "capture_records"

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CaptureStatus.PENDING, index=True
    )
    command_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    raw_payload_ref: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_bundle_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Reference to attached files, images, or voice recording"
    )
    capture_integrity_status: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="ok | hash_mismatch | payload_missing"
    )
    capture_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA-256 of raw_payload_ref content"
    )
