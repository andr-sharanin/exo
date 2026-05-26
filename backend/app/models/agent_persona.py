import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentPersona(Base):
    """
    Dynamic agent persona — configured and trained from Admin Panel.
    Tenant-scoped: each tenant has its own set of agents.

    5 default personas seeded for every new tenant:
      core_advisor, tutor, reflective_support, coach, consultant

    Admins can add unlimited custom personas and train them via:
      - system_prompt: base instruction
      - training_context: accumulated knowledge from past sessions
      - knowledge_base: documents/facts injected into every conversation
      - behavior_rules: specific dos/don'ts
      - tone_style: language register, response length, etc.
    """

    __tablename__ = "agent_personas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
        comment="Tenant isolation — each tenant has its own agent set"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="user_id of admin who created this persona"
    )

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="URL slug for chat: /chat/{entity_type}. Must be unique per tenant."
    )
    avatar_emoji: Mapped[str] = mapped_column(String(8), nullable=False, default="🤖")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Agent kernel (the 'brain' of this persona) ────────────────────────────
    system_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Base system instruction for this persona"
    )
    training_context: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Accumulated knowledge from admin training sessions. "
                "Auto-appended when admin sends training messages."
    )
    knowledge_base: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="[{title, content, added_at}] — documents injected as context into every conversation"
    )
    behavior_rules: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="['Always respond in Russian', 'Never give medical advice', ...]"
    )
    tone_style: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="{language: formal|casual|friendly, response_length: short|medium|long, "
                "uses_emojis: bool, format: prose|bullets|structured}"
    )
    context_window_strategy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="full",
        comment="full|summarize|last_n — how to handle long conversation history"
    )

    # AI routing
    preferred_tier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2,
        comment="1=Mechanical, 2=Analytical, 3=Strategic"
    )
    preferred_model: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="Override model for this persona (e.g. claude-opus-4-7)"
    )

    # State
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="One of the 5 seeded default personas"
    )
    total_conversations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Counter incremented on each new session"
    )
    last_trained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )
