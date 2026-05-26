import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class CalendarIntegration(AuditedModel):
    """
    Stores one calendar connection per user per provider.
    Credentials are encrypted at rest via ConfigService/Fernet.

    providers: caldav | google | microsoft | ical
    """

    __tablename__ = "calendar_integrations"

    provider: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="caldav|google|microsoft|ical"
    )
    display_name: Mapped[str] = mapped_column(String(256), nullable=False, default="My Calendar")
    # CalDAV: base URL; Google/MS: not used (tokens stored in credentials_enc)
    calendar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Fernet-encrypted JSON: {username, password} for CalDAV; {access_token, refresh_token} for OAuth
    credentials_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Google/MS OAuth scopes used
    oauth_scope: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_direction: Mapped[str] = mapped_column(
        String(16), nullable=False, default="read",
        comment="read|write|bidirectional"
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
