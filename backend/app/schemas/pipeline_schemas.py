"""
Pydantic schemas for all 12 canonical pipeline objects.
Pattern: *Create (input) + *Response (output). No update schemas — mutations via FSM.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import AuditedResponse


# ── Command ───────────────────────────────────────────────────────────────────

class CommandCreate(BaseModel):
    ingress_channel: str = Field(..., examples=["web", "mobile", "telegram"])
    ingress_modality: str = Field(..., examples=["text", "voice", "quick_capture"])
    raw_payload_ref: str = Field(..., min_length=1, description="Raw input text or storage URI")
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    idempotency_key: str = Field(..., min_length=1, max_length=256)


class CommandResponse(AuditedResponse):
    ingress_channel: str
    ingress_modality: str
    raw_payload_ref: str
    raw_input: str | None = None
    submitted_at: datetime
    idempotency_key: str
    kernel_status: str | None = None


# ── CaptureRecord ─────────────────────────────────────────────────────────────

class CaptureRecordCreate(BaseModel):
    raw_payload_ref: str
    attachment_bundle_ref: str | None = None
    capture_integrity_status: str = Field(
        ..., examples=["ok", "hash_mismatch", "payload_missing"]
    )
    capture_hash: str = Field(..., description="SHA-256 of raw_payload_ref content")


class CaptureRecordResponse(AuditedResponse):
    command_id: uuid.UUID
    raw_payload_ref: str
    attachment_bundle_ref: str | None
    capture_integrity_status: str
    capture_hash: str


# ── ReasoningArtifact ─────────────────────────────────────────────────────────

class ReasoningArtifactCreate(BaseModel):
    reasoning_stage: str = Field(..., examples=["L0", "L1", "L2", "L3"])
    intent_hypothesis: str
    ambiguity_level: str = Field(..., examples=["none", "low", "medium", "high"])
    actionability_status: str = Field(
        ..., examples=["actionable", "needs_clarification", "non_actionable", "defer_candidate"]
    )
    reasoning_model_role: str = Field(..., description="AI tier + model used")


class ReasoningArtifactResponse(AuditedResponse):
    capture_id: uuid.UUID
    reasoning_stage: str
    intent_hypothesis: str
    ambiguity_level: str
    actionability_status: str
    reasoning_model_role: str


# ── DecisionObject ────────────────────────────────────────────────────────────

class FastTrackRecord(BaseModel):
    rationale: str
    acknowledged_risk: bool
    skipped_reasoning: bool
    time_pressure: bool


class DecisionObjectCreate(BaseModel):
    reasoning_ref: uuid.UUID | None = Field(
        None, description="Null for nano_task or fast_track"
    )
    decision_outcome: str = Field(
        ..., examples=["accept", "defer", "reject", "clarify", "decision_support", "fast_track"]
    )
    confirmed_by_user: bool = False
    fast_track_record: FastTrackRecord | None = Field(
        None, description="Required when decision_outcome=fast_track"
    )


class DecisionObjectResponse(AuditedResponse):
    capture_id: uuid.UUID
    reasoning_ref: uuid.UUID | None
    decision_outcome: str
    confirmed_by_user: bool
    decision_timestamp: datetime | None
    fast_track_record: dict[str, Any] | None


# ── ScheduleObject ────────────────────────────────────────────────────────────

class ScheduleObjectCreate(BaseModel):
    schedule_mode: str = Field(
        ..., examples=["schedule_now", "manual_schedule", "auto_schedule"]
    )
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    schedule_authority_type: str = Field(..., examples=["user", "secretary", "system"])


class ScheduleObjectResponse(AuditedResponse):
    decision_id: uuid.UUID
    schedule_mode: str
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    schedule_authority_type: str


# ── StepObject ────────────────────────────────────────────────────────────────

class StepObjectCreate(BaseModel):
    step_type: str = Field(
        ..., examples=["focus_step", "background_step", "rescue_entry_step"]
    )
    execution_readiness: str = Field(
        ..., examples=["ready", "blocked", "needs_clarification"]
    )
    title: str = Field(..., min_length=1, max_length=512)
    definition_of_done_ref: str | None = None
    step_order: int = Field(1, ge=1)
    estimated_minutes: int | None = Field(None, gt=0)


class StepObjectResponse(AuditedResponse):
    decision_id: uuid.UUID
    step_type: str
    execution_readiness: str
    title: str
    definition_of_done_ref: str | None
    step_order: int
    estimated_minutes: int | None


# ── ExecutionSession ──────────────────────────────────────────────────────────

class ExecutionSessionCreate(BaseModel):
    execution_mode: str = Field(..., examples=["focus", "background", "rescue"])
    session_started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ExecutionSessionResponse(AuditedResponse):
    step_id: uuid.UUID
    session_started_at: datetime
    session_ended_at: datetime | None
    execution_mode: str
    actual_duration_minutes: int | None


# ── WitnessObject ─────────────────────────────────────────────────────────────

class WitnessObjectCreate(BaseModel):
    witness_type: str = Field(..., examples=["passive", "linked", "manual"])
    witness_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    verification_class: str = Field(..., examples=["verified", "reported", "partial"])
    execution_session_id: uuid.UUID | None = None
    evidence_ref: str | None = None


class WitnessObjectResponse(AuditedResponse):
    step_id: uuid.UUID
    execution_session_id: uuid.UUID | None
    witness_type: str
    witness_timestamp: datetime
    verification_class: str
    evidence_ref: str | None


# ── OutcomeObject (terminal — no status field) ────────────────────────────────

class OutcomeObjectCreate(BaseModel):
    witness_id: uuid.UUID
    outcome_type: str = Field(
        ...,
        examples=[
            "completed", "partially_completed", "interrupted",
            "cancelled", "expired", "failed_verification"
        ]
    )
    outcome_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    notes: str | None = None


class OutcomeObjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    step_id: uuid.UUID
    witness_id: uuid.UUID
    outcome_type: str
    outcome_timestamp: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime
    schema_version: int
    sensitivity_class: str


# ── EntitySession ─────────────────────────────────────────────────────────────

class EntitySessionCreate(BaseModel):
    entity_type: str = Field(
        ...,
        examples=["core_advisor", "tutor", "reflective_support", "coach", "consultant"]
    )
    session_mode: str = Field(..., examples=["advisory", "reflection", "planning"])
    context_ref: dict[str, Any] | None = None
    session_started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class EntitySessionResponse(AuditedResponse):
    entity_type: str
    session_mode: str
    context_ref: dict[str, Any] | None
    session_started_at: datetime
    session_ended_at: datetime | None


# ── MemoryObject ──────────────────────────────────────────────────────────────

class MemoryObjectCreate(BaseModel):
    memory_type: str = Field(..., examples=["pattern", "preference", "fact", "context"])
    content_ref: str
    relevance_score: float = Field(0.5, ge=0.0, le=1.0)
    source_object_type: str | None = None
    source_object_id: uuid.UUID | None = None
    expires_at: datetime | None = None


class MemoryObjectResponse(AuditedResponse):
    memory_type: str
    content_ref: str
    relevance_score: float
    source_object_type: str | None
    source_object_id: uuid.UUID | None
    expires_at: datetime | None


# ── BehavioralEvent ───────────────────────────────────────────────────────────

class BehavioralEventCreate(BaseModel):
    behavioral_event_type: str = Field(
        ..., examples=["urge_event", "lapse_event", "recovery_event", "risk_window"]
    )
    event_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    user_declared_flag: bool = True
    trigger_description: str | None = None
    context_ref: dict[str, Any] | None = None


class BehavioralEventResponse(AuditedResponse):
    behavioral_event_type: str
    event_timestamp: datetime
    user_declared_flag: bool
    trigger_description: str | None
    context_ref: dict[str, Any] | None
    policy_response: dict[str, Any] | None = None
