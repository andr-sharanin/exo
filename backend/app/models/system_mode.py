from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class SystemMode(AuditedModel):
    """
    Active system mode for a user. New record per switch; latest switched_at is current.
    No `status` column — the mode value itself is the state.
    7 modes: achiever | harmony | recovery | learning | clarity | crisis | creative
    """

    __tablename__ = "system_modes"

    mode: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="achiever | harmony | recovery | learning | clarity | crisis | creative",
    )
    previous_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    switch_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system_suggested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True = system suggested this switch based on energy state",
    )
    switched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
