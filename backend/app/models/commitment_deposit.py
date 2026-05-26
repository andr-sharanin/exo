import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditedModel


class CommitmentDeposit(AuditedModel):
    """
    Loss aversion mechanic: user pledges funds on a step.
    status: held | released | forfeited  (non-FSM, validated in API layer)
    held      → task completed on time → released (returned)
    held      → deadline missed        → forfeited (to charity/fund)
    Stripe fields are optional — populated when real payment integration is wired.
    """

    __tablename__ = "commitment_deposits"

    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
        comment="Soft-ref to StepObject this deposit is committed on"
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="held", index=True
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    stripe_setup_intent_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    # Populated after setup_intent.succeeded webhook — used to charge on forfeit
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_payment_method_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Populated when we create a PaymentIntent (forfeit charge)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charity_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    forfeited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
