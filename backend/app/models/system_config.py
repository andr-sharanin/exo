from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class SystemConfig(AuditedModel):
    """
    Runtime key-value configuration store.
    Secrets are stored encrypted (Fernet); is_secret=True masks value in API responses.
    Editable by system_admin from Admin UI — no server restart required.
    """

    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="misc", index=True,
        comment="ai_keys | agent_prompts | integrations | stripe | misc"
    )
