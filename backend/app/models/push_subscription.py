import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class PushSubscription(AuditedModel):
    """
    Web Push / Expo Push subscription for a user device.
    endpoint: FCM/APNS push URL or Expo push token
    p256dh / auth: Web Push encryption keys (null for Expo tokens)
    """

    __tablename__ = "push_subscriptions"

    endpoint: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    p256dh: Mapped[str | None] = mapped_column(String(256), nullable=True)
    auth: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
