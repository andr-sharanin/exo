import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DayPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_date: date
    status: str
    items: list[Any]
    energy_state_at_generation: str | None
    system_mode_at_generation: str | None
    total_estimated_minutes: int
    generated_at: datetime
    accepted_at: datetime | None
