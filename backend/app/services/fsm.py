"""
ExoCortex Legal State Transition Map.

All canonical object status mutations MUST go through PipelineFSM.
Any undeclared transition raises IllegalTransitionError — no exceptions.
This is the enforcement layer for the Kernel Data Contract invariants.
"""
from enum import StrEnum


class IllegalTransitionError(Exception):
    def __init__(self, object_type: str, from_status: str, action: str) -> None:
        super().__init__(
            f"[FSM] Illegal transition: {object_type}({from_status}) --[{action}]--> ∅"
        )
        self.object_type = object_type
        self.from_status = from_status
        self.action = action


# ── Status Enums (one per canonical object) ───────────────────────────────────

class CommandStatus(StrEnum):
    PENDING = "pending"
    CAPTURED = "captured"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CaptureStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    INTEGRITY_FAILED = "integrity_failed"


class ReasoningStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    SKIPPED = "skipped"  # nano_task or fast_track bypasses reasoning


class DecisionStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ScheduleStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class StepStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class WitnessStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"


class EntitySessionStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class BehavioralEventStatus(StrEnum):
    RECORDED = "recorded"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


# ── Transition Tables ─────────────────────────────────────────────────────────
# Format: (from_status, action) → to_status
# OutcomeObject has no status transitions — it IS the terminal record.

_TRANSITIONS: dict[str, dict[tuple[str, str], str]] = {
    "Command": {
        ("pending", "capture"):  CommandStatus.CAPTURED,
        ("pending", "expire"):   CommandStatus.EXPIRED,
        ("pending", "cancel"):   CommandStatus.CANCELLED,
    },
    "CaptureRecord": {
        ("pending", "complete"):         CaptureStatus.COMPLETE,
        ("pending", "integrity_fail"):   CaptureStatus.INTEGRITY_FAILED,
    },
    "ReasoningArtifact": {
        ("pending", "complete"):  ReasoningStatus.COMPLETE,
        ("pending", "skip"):      ReasoningStatus.SKIPPED,
    },
    "DecisionObject": {
        ("pending", "confirm"):  DecisionStatus.CONFIRMED,
        ("pending", "reject"):   DecisionStatus.REJECTED,
        ("pending", "expire"):   DecisionStatus.EXPIRED,
    },
    "ScheduleObject": {
        ("pending",   "schedule"):  ScheduleStatus.SCHEDULED,
        ("scheduled", "activate"):  ScheduleStatus.ACTIVE,
        ("scheduled", "cancel"):    ScheduleStatus.CANCELLED,
        ("scheduled", "expire"):    ScheduleStatus.EXPIRED,
        ("active",    "cancel"):    ScheduleStatus.CANCELLED,
    },
    "StepObject": {
        ("pending",     "ready"):     StepStatus.READY,
        ("ready",       "start"):     StepStatus.IN_PROGRESS,
        ("in_progress", "complete"):  StepStatus.COMPLETED,
        ("in_progress", "pause"):     StepStatus.READY,
        ("ready",       "skip"):      StepStatus.SKIPPED,
        ("ready",       "cancel"):    StepStatus.CANCELLED,
        ("in_progress", "cancel"):    StepStatus.CANCELLED,
    },
    "ExecutionSession": {
        ("active",  "pause"):    SessionStatus.PAUSED,
        ("paused",  "resume"):   SessionStatus.ACTIVE,
        ("active",  "complete"): SessionStatus.COMPLETED,
        ("paused",  "complete"): SessionStatus.COMPLETED,
        ("active",  "abandon"):  SessionStatus.ABANDONED,
        ("paused",  "abandon"):  SessionStatus.ABANDONED,
    },
    "WitnessObject": {
        ("pending", "complete"): WitnessStatus.COMPLETE,
    },
    "EntitySession": {
        ("active", "close"): EntitySessionStatus.CLOSED,
    },
    "MemoryObject": {
        ("active",   "expire"):   MemoryStatus.EXPIRED,
        ("active",   "archive"):  MemoryStatus.ARCHIVED,
        ("expired",  "archive"):  MemoryStatus.ARCHIVED,
    },
    "BehavioralEvent": {
        ("recorded",     "acknowledge"):  BehavioralEventStatus.ACKNOWLEDGED,
        ("acknowledged", "resolve"):      BehavioralEventStatus.RESOLVED,
    },
}


class PipelineFSM:
    """
    Singleton FSM enforcing the ExoCortex Legal State Transition Map.
    Stateless — safe to use as a module-level singleton.
    """

    def transition(self, object_type: str, from_status: str, action: str) -> str:
        """Returns the next status or raises IllegalTransitionError."""
        table = _TRANSITIONS.get(object_type)
        if table is None:
            raise ValueError(f"Unknown canonical object type: '{object_type}'")
        next_status = table.get((from_status, action))
        if next_status is None:
            raise IllegalTransitionError(object_type, from_status, action)
        return next_status

    def allowed_actions(self, object_type: str, from_status: str) -> list[str]:
        """Returns actions valid from the given status (for API introspection)."""
        table = _TRANSITIONS.get(object_type, {})
        return [action for (status, action) in table if status == from_status]

    def is_terminal(self, object_type: str, status: str) -> bool:
        """True if no outgoing transitions exist from this status."""
        table = _TRANSITIONS.get(object_type, {})
        return not any(s == status for (s, _) in table)


fsm = PipelineFSM()
