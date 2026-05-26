"""
UserSubscription — tracks the billing tier for each user.

Tiers:
  free  — one user, basic features, limited quotas
  pro   — all features, unlimited quotas, x2 governance, all calendar providers
  team  — all pro + multiple users per tenant (tenant admin manages members)

Status mirrors Stripe subscription states:
  active    — paid and current
  trialing  — in trial period
  past_due  — payment failed, grace period active
  canceled  — subscription ended, user downgraded to free
  free      — no Stripe subscription (default)

stripe_subscription_id and stripe_customer_id are nullable for free tier.
current_period_end is populated from Stripe and used to check active status.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    tier: Mapped[str] = mapped_column(
        String(16), nullable=False, default="free",
        comment="free|pro|team"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="free",
        comment="free|active|trialing|past_due|canceled"
    )

    # Stripe fields — populated when user upgrades
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Billing period — null for free tier
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
