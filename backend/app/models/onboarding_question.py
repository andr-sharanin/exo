import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OnboardingQuestion(Base):
    """
    Configurable onboarding question — managed from Admin Panel.
    NOT tenant-scoped: these are system-wide templates.
    system_admin creates/edits questions; all tenants use them.
    """

    __tablename__ = "onboarding_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sub_text: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Additional explanation shown below the question"
    )
    answer_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="scale_1_5|choice|multi_choice|text"
    )
    options: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="For choice/multi_choice: [{value: str, label: str, dimension_impact: {}}]"
    )
    # Which behavioral dimension this question measures
    dimension: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="focus_stability|task_handling_style|decision_style|... maps to PolicyKernel fields"
    )
    weight: Mapped[float | None] = mapped_column(
        nullable=True, default=1.0,
        comment="Multiplier when computing dimension score"
    )
    mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="both",
        comment="quick|deep|both — which onboarding mode includes this question"
    )
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Display order within the mode"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    category: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="focus|decision|energy|execution|social — question grouping"
    )
