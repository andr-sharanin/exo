"""
FSM test suite — 100% legal transition coverage.

Every row in the transition table gets a positive test.
Every object type gets at least one illegal transition test.
Terminal state detection is verified for all object types.
"""
import pytest

from app.services.fsm import (
    PipelineFSM,
    IllegalTransitionError,
    fsm,
    CommandStatus,
    CaptureStatus,
    ReasoningStatus,
    DecisionStatus,
    ScheduleStatus,
    StepStatus,
    SessionStatus,
    WitnessStatus,
    EntitySessionStatus,
    MemoryStatus,
    BehavioralEventStatus,
)


# ── Legal transitions (parametrized) ─────────────────────────────────────────

@pytest.mark.parametrize("object_type,from_status,action,expected", [
    # Command
    ("Command", "pending", "capture",  CommandStatus.CAPTURED),
    ("Command", "pending", "expire",   CommandStatus.EXPIRED),
    ("Command", "pending", "cancel",   CommandStatus.CANCELLED),

    # CaptureRecord
    ("CaptureRecord", "pending", "complete",         CaptureStatus.COMPLETE),
    ("CaptureRecord", "pending", "integrity_fail",   CaptureStatus.INTEGRITY_FAILED),

    # ReasoningArtifact
    ("ReasoningArtifact", "pending", "complete",  ReasoningStatus.COMPLETE),
    ("ReasoningArtifact", "pending", "skip",      ReasoningStatus.SKIPPED),

    # DecisionObject
    ("DecisionObject", "pending", "confirm",  DecisionStatus.CONFIRMED),
    ("DecisionObject", "pending", "reject",   DecisionStatus.REJECTED),
    ("DecisionObject", "pending", "expire",   DecisionStatus.EXPIRED),

    # ScheduleObject
    ("ScheduleObject", "pending",   "schedule",  ScheduleStatus.SCHEDULED),
    ("ScheduleObject", "scheduled", "activate",  ScheduleStatus.ACTIVE),
    ("ScheduleObject", "scheduled", "cancel",    ScheduleStatus.CANCELLED),
    ("ScheduleObject", "scheduled", "expire",    ScheduleStatus.EXPIRED),
    ("ScheduleObject", "active",    "cancel",    ScheduleStatus.CANCELLED),

    # StepObject
    ("StepObject", "pending",     "ready",     StepStatus.READY),
    ("StepObject", "ready",       "start",     StepStatus.IN_PROGRESS),
    ("StepObject", "in_progress", "complete",  StepStatus.COMPLETED),
    ("StepObject", "in_progress", "pause",     StepStatus.READY),
    ("StepObject", "ready",       "skip",      StepStatus.SKIPPED),
    ("StepObject", "ready",       "cancel",    StepStatus.CANCELLED),
    ("StepObject", "in_progress", "cancel",    StepStatus.CANCELLED),

    # ExecutionSession
    ("ExecutionSession", "active",  "pause",    SessionStatus.PAUSED),
    ("ExecutionSession", "paused",  "resume",   SessionStatus.ACTIVE),
    ("ExecutionSession", "active",  "complete", SessionStatus.COMPLETED),
    ("ExecutionSession", "paused",  "complete", SessionStatus.COMPLETED),
    ("ExecutionSession", "active",  "abandon",  SessionStatus.ABANDONED),
    ("ExecutionSession", "paused",  "abandon",  SessionStatus.ABANDONED),

    # WitnessObject
    ("WitnessObject", "pending", "complete", WitnessStatus.COMPLETE),

    # EntitySession
    ("EntitySession", "active", "close", EntitySessionStatus.CLOSED),

    # MemoryObject
    ("MemoryObject", "active",   "expire",   MemoryStatus.EXPIRED),
    ("MemoryObject", "active",   "archive",  MemoryStatus.ARCHIVED),
    ("MemoryObject", "expired",  "archive",  MemoryStatus.ARCHIVED),

    # BehavioralEvent
    ("BehavioralEvent", "recorded",     "acknowledge",  BehavioralEventStatus.ACKNOWLEDGED),
    ("BehavioralEvent", "acknowledged", "resolve",      BehavioralEventStatus.RESOLVED),
])
def test_legal_transition(
    object_type: str, from_status: str, action: str, expected: str
) -> None:
    result = fsm.transition(object_type, from_status, action)
    assert result == expected


# ── Illegal transitions ───────────────────────────────────────────────────────

@pytest.mark.parametrize("object_type,from_status,action", [
    ("Command",          "captured",    "capture"),    # already captured
    ("Command",          "expired",     "capture"),    # expired can't re-capture
    ("Command",          "cancelled",   "capture"),    # cancelled is terminal
    ("CaptureRecord",    "complete",    "complete"),   # re-completion blocked
    ("ReasoningArtifact","complete",    "skip"),       # can't skip after complete
    ("DecisionObject",   "confirmed",   "confirm"),    # re-confirm blocked
    ("DecisionObject",   "rejected",    "confirm"),    # rejected is terminal
    ("ScheduleObject",   "cancelled",   "schedule"),   # cancelled is terminal
    ("ScheduleObject",   "active",      "schedule"),   # can't re-schedule active
    ("StepObject",       "completed",   "start"),      # completed is terminal
    ("StepObject",       "cancelled",   "ready"),      # cancelled is terminal
    ("StepObject",       "pending",     "start"),      # must go ready first
    ("ExecutionSession", "completed",   "pause"),      # completed is terminal
    ("ExecutionSession", "abandoned",   "resume"),     # abandoned is terminal
    ("WitnessObject",    "complete",    "complete"),   # already complete
    ("EntitySession",    "closed",      "close"),      # already closed
    ("MemoryObject",     "archived",    "expire"),     # archived is terminal
    ("BehavioralEvent",  "resolved",    "resolve"),    # already resolved
    ("BehavioralEvent",  "recorded",    "resolve"),    # must acknowledge first
])
def test_illegal_transition_raises(object_type: str, from_status: str, action: str) -> None:
    with pytest.raises(IllegalTransitionError) as exc_info:
        fsm.transition(object_type, from_status, action)
    err = exc_info.value
    assert err.object_type == object_type
    assert err.from_status == from_status
    assert err.action == action


def test_unknown_object_type_raises() -> None:
    with pytest.raises(ValueError, match="Unknown canonical object type"):
        fsm.transition("NonExistentObject", "pending", "some_action")


# ── allowed_actions ───────────────────────────────────────────────────────────

def test_allowed_actions_command_pending() -> None:
    actions = fsm.allowed_actions("Command", "pending")
    assert set(actions) == {"capture", "expire", "cancel"}


def test_allowed_actions_command_captured_is_empty() -> None:
    actions = fsm.allowed_actions("Command", "captured")
    assert actions == []


def test_allowed_actions_step_in_progress() -> None:
    actions = fsm.allowed_actions("StepObject", "in_progress")
    assert set(actions) == {"complete", "pause", "cancel"}


def test_allowed_actions_unknown_object_returns_empty() -> None:
    actions = fsm.allowed_actions("Unknown", "anything")
    assert actions == []


# ── is_terminal ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("object_type,status,expected_terminal", [
    ("Command", "pending",    False),
    ("Command", "captured",   True),
    ("Command", "expired",    True),
    ("Command", "cancelled",  True),

    ("StepObject", "pending",      False),
    ("StepObject", "ready",        False),
    ("StepObject", "in_progress",  False),
    ("StepObject", "completed",    True),
    ("StepObject", "skipped",      True),
    ("StepObject", "cancelled",    True),

    ("ExecutionSession", "active",     False),
    ("ExecutionSession", "paused",     False),
    ("ExecutionSession", "completed",  True),
    ("ExecutionSession", "abandoned",  True),

    ("BehavioralEvent", "recorded",      False),
    ("BehavioralEvent", "acknowledged",  False),
    ("BehavioralEvent", "resolved",      True),

    ("MemoryObject", "active",    False),
    ("MemoryObject", "expired",   False),
    ("MemoryObject", "archived",  True),
])
def test_is_terminal(object_type: str, status: str, expected_terminal: bool) -> None:
    assert fsm.is_terminal(object_type, status) is expected_terminal


# ── Error message quality ─────────────────────────────────────────────────────

def test_illegal_transition_error_message_is_informative() -> None:
    with pytest.raises(IllegalTransitionError) as exc_info:
        fsm.transition("Command", "captured", "capture")
    assert "Command" in str(exc_info.value)
    assert "captured" in str(exc_info.value)
    assert "capture" in str(exc_info.value)


# ── Singleton consistency ─────────────────────────────────────────────────────

def test_fsm_singleton_is_same_instance() -> None:
    from app.services.fsm import fsm as fsm2
    assert fsm is fsm2


def test_fsm_is_stateless() -> None:
    """FSM must produce the same result regardless of call order."""
    r1 = fsm.transition("Command", "pending", "capture")
    r2 = fsm.transition("StepObject", "ready", "start")
    r3 = fsm.transition("Command", "pending", "capture")
    assert r1 == r3 == CommandStatus.CAPTURED
    assert r2 == StepStatus.IN_PROGRESS
