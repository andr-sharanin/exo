import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReviewTemplate(Base):
    """
    Планёрка template — configured from Admin Panel.
    Defines structure for daily/weekly/monthly review sessions.

    Daily  — утренняя: AI prepares the day, user confirms (Parabellum: think once, then execute)
    Weekly — Friday evening: what worked, what didn't, adjust weekly focus
    Monthly — end of month: strategic recalibration, update StrategicKernel
    """

    __tablename__ = "review_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    review_type: Mapped[str] = mapped_column(
        String(16), nullable=False,
        comment="daily|weekly|monthly"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Questions shown to user during this review
    questions: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="[{id, text, answer_type, options, required}]"
    )

    # AI context instructions: what AI should analyze before showing questions
    ai_prep_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="System prompt for AI to generate review insights/agenda"
    )

    # Schedule config (interpreted by ARQ scheduler)
    schedule_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="daily: {hour: 7, minute: 0} | weekly: {weekday: 4, hour: 18} | monthly: {day: -1, hour: 9}"
    )

    # What to do with strategic kernel after completion
    updates_strategic_kernel: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="If True, service rebuilds StrategicKernel after completion"
    )

    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Default template used when no custom template exists"
    )
