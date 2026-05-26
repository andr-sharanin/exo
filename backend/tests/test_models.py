"""
Model integrity tests.
Verifies: required fields, sensitivity_class enforcement, defaults.
Does not test DB persistence (that's integration — covered in Phase 2 tests).
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.models.behavioral_event import BehavioralEvent
from app.models.base import SensitivityClass
from app.models.command import Command


def _base_kwargs() -> dict:
    return {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
    }


def test_behavioral_event_always_high_sensitive() -> None:
    """BehavioralEvent must be high_sensitive regardless of what caller passes."""
    event = BehavioralEvent(
        **_base_kwargs(),
        behavioral_event_type="urge_event",
        event_timestamp=datetime.now(timezone.utc),
        user_declared_flag=True,
        # Attempt to override sensitivity — must be silently corrected
        sensitivity_class=SensitivityClass.STANDARD,
    )
    assert event.sensitivity_class == SensitivityClass.HIGH_SENSITIVE


def test_behavioral_event_high_sensitive_stays_high_sensitive() -> None:
    event = BehavioralEvent(
        **_base_kwargs(),
        behavioral_event_type="lapse_event",
        event_timestamp=datetime.now(timezone.utc),
        user_declared_flag=False,
    )
    assert event.sensitivity_class == SensitivityClass.HIGH_SENSITIVE


def test_command_default_status_is_pending() -> None:
    cmd = Command(
        **_base_kwargs(),
        ingress_channel="web",
        ingress_modality="text",
        raw_payload_ref="Buy milk",
        submitted_at=datetime.now(timezone.utc),
        idempotency_key=str(uuid.uuid4()),
    )
    assert cmd.status == "pending"


def test_command_default_sensitivity_is_standard() -> None:
    cmd = Command(
        **_base_kwargs(),
        ingress_channel="web",
        ingress_modality="text",
        raw_payload_ref="Buy milk",
        submitted_at=datetime.now(timezone.utc),
        idempotency_key=str(uuid.uuid4()),
    )
    assert cmd.sensitivity_class == SensitivityClass.STANDARD
