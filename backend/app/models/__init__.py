# Import all models so they register on Base.metadata before Alembic migrations.
from app.models.base import AuditedModel, SensitivityClass
from app.models.audit_log import AuditLog
from app.models.command import Command
from app.models.capture_record import CaptureRecord
from app.models.reasoning_artifact import ReasoningArtifact
from app.models.decision_object import DecisionObject
from app.models.schedule_object import ScheduleObject
from app.models.step_object import StepObject
from app.models.execution_session import ExecutionSession
from app.models.witness_object import WitnessObject
from app.models.outcome_object import OutcomeObject
from app.models.entity_session import EntitySession
from app.models.memory_object import MemoryObject
from app.models.behavioral_event import BehavioralEvent
# Phase 4 — Behavioral & Energy Layer
from app.models.energy_score import EnergyScore
from app.models.system_mode import SystemMode
from app.models.client_kernel_profile import ClientKernelProfile
# Phase 5 — Onboarding & Kernel Calibration
from app.models.onboarding_session import OnboardingSession, OnboardingSessionStatus
# Phase 6 — AI Layer
from app.models.ai_request_log import AIRequestLog
# Phase 7 — Secretary & Agent System
from app.models.day_plan import DayPlan
from app.models.agent_message import AgentMessage
# Phase 8 — Planning Horizons & Deposit
from app.models.planning_goal import PlanningGoal
from app.models.commitment_deposit import CommitmentDeposit
# Phase 9 — System Configuration + Integrations
from app.models.system_config import SystemConfig
from app.models.push_subscription import PushSubscription
# Phase 12 — Telegram + Calendar
from app.models.telegram_user import TelegramUser
from app.models.calendar_integration import CalendarIntegration
# Governance ADR
from app.models.governance import GovernanceSetting, GovernanceRecord
# Subscriptions / tiers
from app.models.subscription import UserSubscription
# Team management
from app.models.team_invitation import TeamInvitation

__all__ = [
    "AuditedModel",
    "SensitivityClass",
    "AuditLog",
    "Command",
    "CaptureRecord",
    "ReasoningArtifact",
    "DecisionObject",
    "ScheduleObject",
    "StepObject",
    "ExecutionSession",
    "WitnessObject",
    "OutcomeObject",
    "EntitySession",
    "MemoryObject",
    "BehavioralEvent",
    "EnergyScore",
    "SystemMode",
    "ClientKernelProfile",
    "OnboardingSession",
    "OnboardingSessionStatus",
    "AIRequestLog",
    "DayPlan",
    "AgentMessage",
    "PlanningGoal",
    "CommitmentDeposit",
    "SystemConfig",
    "PushSubscription",
    "TelegramUser",
    "CalendarIntegration",
    "GovernanceSetting",
    "GovernanceRecord",
    "UserSubscription",
    "TeamInvitation",
]
