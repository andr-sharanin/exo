import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

_VALID_HORIZONS = frozenset([
    "vision", "annual", "quarterly", "monthly", "weekly", "daily",
])


class PlanningGoalCreate(BaseModel):
    title: str
    horizon: str
    description: str | None = None
    parent_id: uuid.UUID | None = None
    target_date: date | None = None

    @field_validator("horizon")
    @classmethod
    def validate_horizon(cls, v: str) -> str:
        if v not in _VALID_HORIZONS:
            raise ValueError(f"horizon must be one of {sorted(_VALID_HORIZONS)}")
        return v


class PlanningGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    horizon: str
    title: str
    description: str | None
    status: str
    parent_id: uuid.UUID | None
    target_date: date | None
    completed_at: datetime | None
