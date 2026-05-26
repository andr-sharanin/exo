import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class AIRequestLog(AuditedModel):
    """
    Immutable audit trail for every AI inference call.
    Append-only — status is set at creation and never mutated.
    status: "success" | "error"
    """

    __tablename__ = "ai_request_logs"

    stage: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    model_used: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="success", index=True
    )
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    was_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    object_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Optional soft-ref to the pipeline object this call was made for",
    )
