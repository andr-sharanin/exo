"""Pydantic schemas for Phase 5: Onboarding & Kernel Calibration."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.onboarding import OnboardingMode


# ── Request / response for question options (read-only, sent to client) ────────

class QuestionOptionDTO(BaseModel):
    option_id: str
    text: str


class QuestionDTO(BaseModel):
    question_id: str
    scenario: str
    options: list[QuestionOptionDTO]


# ── POST /onboarding/start ────────────────────────────────────────────────────

class OnboardingStartRequest(BaseModel):
    mode: OnboardingMode


class OnboardingStartResponse(BaseModel):
    session_id: uuid.UUID
    mode: str
    questions: list[QuestionDTO]
    total_questions: int


# ── POST /onboarding/submit ───────────────────────────────────────────────────

class AnswerItem(BaseModel):
    question_id: str = Field(..., min_length=1)
    option_id: str = Field(..., min_length=1)


class OnboardingSubmitRequest(BaseModel):
    session_id: uuid.UUID
    answers: list[AnswerItem] = Field(..., min_length=1)


# ── POST /onboarding/recalibrate ──────────────────────────────────────────────

class RecalibrateRequest(BaseModel):
    lookback_days: int = Field(30, ge=7, le=365)


# ── Internal: stored session (not returned to client directly) ────────────────

class OnboardingSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    mode: str
    status: str
    profile_id: uuid.UUID | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
