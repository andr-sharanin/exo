import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class TelegramUser(AuditedModel):
    """
    Links a Telegram chat_id to an ExoCortex user.
    Created when user runs /link <token> in Telegram.
    """

    __tablename__ = "telegram_users"

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True, index=True
    )
    telegram_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
