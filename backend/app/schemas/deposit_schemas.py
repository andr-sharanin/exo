import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator


class CommitmentDepositCreate(BaseModel):
    step_id: uuid.UUID
    amount_cents: int
    currency: str = "USD"
    due_date: date

    @field_validator("amount_cents")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_cents must be positive")
        return v

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("due_date must be today or in the future")
        return v


class CommitmentDepositResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    step_id: uuid.UUID
    amount_cents: int
    currency: str
    status: str
    due_date: date
    stripe_setup_intent_id: str | None
    stripe_customer_id: str | None
    stripe_payment_method_id: str | None
    stripe_payment_intent_id: str | None
    charity_ref: str | None
    released_at: datetime | None
    forfeited_at: datetime | None
