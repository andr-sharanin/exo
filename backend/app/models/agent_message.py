import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class AgentMessage(AuditedModel):
    """
    Individual message in an EntitySession conversation.
    role: "user" | "assistant"
    Append-only — messages are never mutated after creation.
    """

    __tablename__ = "agent_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_order: Mapped[int] = mapped_column(Integer, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
