"""Pydantic schemas for Phase 4: Energy, System Mode, ClientKernelProfile."""
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SystemModeType(StrEnum):
    ACHIEVER = "achiever"    # Достигатор — maximum output, hard timers
    HARMONY = "harmony"      # Гармония   — work-life balance
    RECOVERY = "recovery"    # Восстановление — 1-3 tasks, gentle
    LEARNING = "learning"    # Обучение   — long focus sessions, tutor agent
    CLARITY = "clarity"      # Прояснение — reason stage only, priority review
    CRISIS = "crisis"        # Кризис     — triage, critical tasks only
    CREATIVE = "creative"    # Творческий — long unstructured blocks


# ── Energy Check-in ───────────────────────────────────────────────────────────

class EnergyCheckinCreate(BaseModel):
    sleep_quality: int = Field(..., ge=1, le=5, description="Sleep quality last night (1=poor, 5=excellent)")
    mood: int = Field(..., ge=1, le=5, description="Current mood (1=low, 5=high)")
    energy_level: int = Field(..., ge=1, le=5, description="Subjective energy level (1=depleted, 5=full)")
    note: str | None = Field(None, max_length=500)


class EnergyOverrideCreate(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Manual energy score 0–100")
    reason: str = Field(..., min_length=1, max_length=500)


class EnergyScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    score: int
    state: str
    is_override: bool
    valid_until: datetime
    created_at: datetime
    suggested_mode: str | None = None


# ── System Mode ───────────────────────────────────────────────────────────────

class ModeSwitchRequest(BaseModel):
    mode: SystemModeType
    reason: str | None = Field(None, max_length=500)


class SystemModeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    mode: str
    previous_mode: str | None
    switch_reason: str | None
    is_system_suggested: bool
    switched_at: datetime
    created_at: datetime


# ── ClientKernelProfile ───────────────────────────────────────────────────────

class ClientKernelProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    calibration_version: int
    calibrated_at: datetime
    profile_data: dict[str, Any]
    computed_defaults: dict[str, Any]
    created_at: datetime
