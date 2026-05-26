"""Pydantic schemas for Phase 6: AI Layer and Admin Panel."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai_router import PipelineStage


# ── AI Classify ───────────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    context: dict[str, Any] | None = None


class ClassifyResponse(BaseModel):
    request_id: uuid.UUID
    tier: str
    model_used: str
    intent_class: str
    urgency: str
    complexity: str
    confidence: float
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    was_fallback: bool


# ── AI Reason ─────────────────────────────────────────────────────────────────

class ReasonRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    intent_class: str = Field(..., examples=["task", "question", "idea"])
    complexity: str = Field("medium", examples=["low", "medium", "high"])
    energy_state: str = Field("sufficient", examples=["sufficient", "constrained", "critical"])
    context: dict[str, Any] | None = None


class ReasonResponse(BaseModel):
    request_id: uuid.UUID
    tier: str
    model_used: str
    intent_hypothesis: str
    ambiguity_level: str
    actionability_status: str
    reasoning: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    was_fallback: bool


# ── AI Advisory ───────────────────────────────────────────────────────────────

class AdvisoryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    energy_state: str = Field("sufficient", examples=["sufficient", "constrained", "critical"])
    system_mode: str = Field("harmony")
    context: dict[str, Any] | None = None


class AdvisoryResponse(BaseModel):
    request_id: uuid.UUID
    tier: str
    model_used: str
    response: str
    suggestions: list[str]
    confidence: float
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    was_fallback: bool


# ── AIRequestLog (read) ───────────────────────────────────────────────────────

class AIRequestLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    stage: str
    tier: str
    model_used: str
    status: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    was_fallback: bool
    error_type: str | None
    created_at: datetime


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminHealthResponse(BaseModel):
    status: str
    ai_tiers: list[str]
    timestamp: datetime


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    object_type: str
    object_id: uuid.UUID
    action: str
    from_status: str | None
    to_status: str | None
    occurred_at: datetime


class AdminAuditResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    limit: int
    offset: int


class AIStatsResponse(BaseModel):
    total_requests: int
    by_tier: dict[str, int]
    total_prompt_tokens: int
    total_completion_tokens: int
    success_rate: float
    fallback_rate: float
