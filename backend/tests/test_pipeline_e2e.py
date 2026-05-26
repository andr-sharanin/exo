"""
Phase 2 E2E test — full pipeline: Command → OutcomeObject.
Also covers: nano_task flow, fast_track flow, FSM enforcement via API.
"""
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


async def _transition(client: AsyncClient, slug: str, obj_id: str, action: str) -> dict:
    resp = await client.post(
        f"/api/v1/transition/{slug}/{obj_id}",
        json={"action": action},
    )
    assert resp.status_code == 200, f"Transition {slug}[{obj_id}] --[{action}]--> failed: {resp.text}"
    return resp.json()


# ── Full canonical pipeline ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_command_to_outcome(client: AsyncClient) -> None:
    idem_key = _uid()

    # 1. Create Command
    r = await client.post("/api/v1/commands", json={
        "ingress_channel": "web",
        "ingress_modality": "text",
        "raw_payload_ref": "Finish quarterly report",
        "submitted_at": _now(),
        "idempotency_key": idem_key,
    })
    assert r.status_code == 201
    cmd = r.json()
    assert cmd["status"] == "pending"
    cmd_id = cmd["id"]

    # 2. Create CaptureRecord (auto-transitions Command → captured)
    r = await client.post(f"/api/v1/commands/{cmd_id}/capture", json={
        "raw_payload_ref": "Finish quarterly report",
        "capture_integrity_status": "ok",
        "capture_hash": "abc123def456" * 4,
    })
    assert r.status_code == 201
    cap = r.json()
    assert cap["status"] == "pending"
    cap_id = cap["id"]

    # Verify Command was transitioned to captured
    r = await client.get(f"/api/v1/commands/{cmd_id}")
    assert r.json()["status"] == "captured"

    # 3. Transition CaptureRecord → complete
    await _transition(client, "capture-records", cap_id, "complete")

    # 4. Create ReasoningArtifact
    r = await client.post(f"/api/v1/capture/{cap_id}/reason", json={
        "reasoning_stage": "L1",
        "intent_hypothesis": "User wants to complete Q3 financial report",
        "ambiguity_level": "low",
        "actionability_status": "actionable",
        "reasoning_model_role": "tier2/claude-sonnet",
    })
    assert r.status_code == 201
    reason = r.json()
    reason_id = reason["id"]

    # 5. Transition ReasoningArtifact → complete
    await _transition(client, "reasoning-artifacts", reason_id, "complete")

    # 6. Create DecisionObject (user confirms)
    r = await client.post(f"/api/v1/capture/{cap_id}/decide", json={
        "reasoning_ref": reason_id,
        "decision_outcome": "accept",
        "confirmed_by_user": True,
    })
    assert r.status_code == 201
    decision = r.json()
    assert decision["confirmed_by_user"] is True
    dec_id = decision["id"]

    # 7. Transition Decision → confirmed
    await _transition(client, "decisions", dec_id, "confirm")

    # 8. Create ScheduleObject
    r = await client.post(f"/api/v1/decisions/{dec_id}/schedule", json={
        "schedule_mode": "schedule_now",
        "scheduled_start": _now(),
        "schedule_authority_type": "user",
    })
    assert r.status_code == 201
    sched_id = r.json()["id"]

    # 9. Transition Schedule: pending → scheduled → active
    await _transition(client, "schedules", sched_id, "schedule")
    await _transition(client, "schedules", sched_id, "activate")

    # 10. Create StepObject
    r = await client.post(f"/api/v1/decisions/{dec_id}/steps", json={
        "step_type": "focus_step",
        "execution_readiness": "ready",
        "title": "Write executive summary",
        "step_order": 1,
        "estimated_minutes": 45,
    })
    assert r.status_code == 201
    step = r.json()
    step_id = step["id"]

    # 11. Transition Step: pending → ready → in_progress
    await _transition(client, "steps", step_id, "ready")
    await _transition(client, "steps", step_id, "start")

    # 12. Create ExecutionSession
    r = await client.post(f"/api/v1/steps/{step_id}/sessions", json={
        "execution_mode": "focus",
        "session_started_at": _now(),
    })
    assert r.status_code == 201
    session_id = r.json()["id"]

    # 13. Transition Session → completed
    await _transition(client, "sessions", session_id, "complete")

    # 14. Create WitnessObject (passive, verified)
    r = await client.post(f"/api/v1/steps/{step_id}/witness", json={
        "witness_type": "passive",
        "witness_timestamp": _now(),
        "verification_class": "verified",
        "execution_session_id": session_id,
    })
    assert r.status_code == 201
    witness_id = r.json()["id"]

    # 15. Transition Witness → complete
    await _transition(client, "witnesses", witness_id, "complete")

    # 16. Create OutcomeObject (terminal)
    r = await client.post(f"/api/v1/steps/{step_id}/outcome", json={
        "witness_id": witness_id,
        "outcome_type": "completed",
        "outcome_timestamp": _now(),
        "notes": "Q3 report finished on time",
    })
    assert r.status_code == 201
    outcome = r.json()
    assert outcome["outcome_type"] == "completed"
    assert outcome["step_id"] == step_id


# ── Idempotency ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_command_idempotency(client: AsyncClient) -> None:
    key = _uid()
    payload = {
        "ingress_channel": "web",
        "ingress_modality": "text",
        "raw_payload_ref": "Idempotent command",
        "submitted_at": _now(),
        "idempotency_key": key,
    }
    r1 = await client.post("/api/v1/commands", json=payload)
    r2 = await client.post("/api/v1/commands", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


# ── FSM enforcement via API ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_illegal_transition_returns_409(client: AsyncClient) -> None:
    r = await client.post("/api/v1/commands", json={
        "ingress_channel": "web",
        "ingress_modality": "text",
        "raw_payload_ref": "Test",
        "submitted_at": _now(),
        "idempotency_key": _uid(),
    })
    cmd_id = r.json()["id"]

    # capture is legal
    await _transition(client, "commands", cmd_id, "capture")

    # capture again is ILLEGAL — already captured
    r = await client.post(
        f"/api/v1/transition/commands/{cmd_id}",
        json={"action": "capture"},
    )
    assert r.status_code == 409
    assert "Illegal transition" in r.json()["detail"]


# ── Witness constraint: manual cannot produce verified ────────────────────────

@pytest.mark.asyncio
async def test_manual_witness_cannot_be_verified(client: AsyncClient) -> None:
    # Create a minimal step to test against
    cmd_r = await client.post("/api/v1/commands", json={
        "ingress_channel": "web", "ingress_modality": "text",
        "raw_payload_ref": "Test", "submitted_at": _now(), "idempotency_key": _uid(),
    })
    cmd_id = cmd_r.json()["id"]

    cap_r = await client.post(f"/api/v1/commands/{cmd_id}/capture", json={
        "raw_payload_ref": "Test", "capture_integrity_status": "ok",
        "capture_hash": "x" * 48,
    })
    cap_id = cap_r.json()["id"]

    # Skip reasoning — use fast_track decision
    dec_r = await client.post(f"/api/v1/capture/{cap_id}/decide", json={
        "decision_outcome": "fast_track",
        "confirmed_by_user": True,
        "fast_track_record": {
            "rationale": "trivial task",
            "acknowledged_risk": True,
            "skipped_reasoning": True,
            "time_pressure": False,
        },
    })
    dec_id = dec_r.json()["id"]

    step_r = await client.post(f"/api/v1/decisions/{dec_id}/steps", json={
        "step_type": "focus_step",
        "execution_readiness": "ready",
        "title": "Quick task",
        "step_order": 1,
    })
    step_id = step_r.json()["id"]

    # Manual witness attempting verified — must fail
    r = await client.post(f"/api/v1/steps/{step_id}/witness", json={
        "witness_type": "manual",
        "witness_timestamp": _now(),
        "verification_class": "verified",
    })
    assert r.status_code == 422
    assert "manual witness" in r.json()["detail"].lower()


# ── outcome=completed requires verified witness ───────────────────────────────

@pytest.mark.asyncio
async def test_completed_outcome_requires_verified_witness(client: AsyncClient) -> None:
    # Build minimal command → step
    cmd_id = (await client.post("/api/v1/commands", json={
        "ingress_channel": "web", "ingress_modality": "text",
        "raw_payload_ref": "Test", "submitted_at": _now(), "idempotency_key": _uid(),
    })).json()["id"]

    cap_id = (await client.post(f"/api/v1/commands/{cmd_id}/capture", json={
        "raw_payload_ref": "Test", "capture_integrity_status": "ok", "capture_hash": "y" * 48,
    })).json()["id"]

    dec_id = (await client.post(f"/api/v1/capture/{cap_id}/decide", json={
        "decision_outcome": "accept", "confirmed_by_user": True,
    })).json()["id"]

    step_id = (await client.post(f"/api/v1/decisions/{dec_id}/steps", json={
        "step_type": "focus_step", "execution_readiness": "ready",
        "title": "Task", "step_order": 1,
    })).json()["id"]

    # Create witness with partial (not verified)
    witness_id = (await client.post(f"/api/v1/steps/{step_id}/witness", json={
        "witness_type": "manual", "witness_timestamp": _now(),
        "verification_class": "partial",
    })).json()["id"]

    # Try to create completed outcome with partial witness — must fail
    r = await client.post(f"/api/v1/steps/{step_id}/outcome", json={
        "witness_id": witness_id,
        "outcome_type": "completed",
        "outcome_timestamp": _now(),
    })
    assert r.status_code == 422
    assert "verified" in r.json()["detail"].lower()


# ── nano_task flow (no reason/decide) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_nano_task_flow(client: AsyncClient) -> None:
    """nano_task: Command → Capture → Decision(no reasoning) → Step → Session → Witness → Outcome"""
    cmd_id = (await client.post("/api/v1/commands", json={
        "ingress_channel": "mobile", "ingress_modality": "quick_capture",
        "raw_payload_ref": "Buy milk", "submitted_at": _now(), "idempotency_key": _uid(),
    })).json()["id"]

    cap_id = (await client.post(f"/api/v1/commands/{cmd_id}/capture", json={
        "raw_payload_ref": "Buy milk", "capture_integrity_status": "ok",
        "capture_hash": "z" * 48,
    })).json()["id"]

    # Decision with no reasoning_ref (nano_task)
    dec_id = (await client.post(f"/api/v1/capture/{cap_id}/decide", json={
        "reasoning_ref": None,
        "decision_outcome": "accept",
        "confirmed_by_user": True,
    })).json()["id"]

    step_id = (await client.post(f"/api/v1/decisions/{dec_id}/steps", json={
        "step_type": "focus_step", "execution_readiness": "ready",
        "title": "Buy milk at the store", "step_order": 1, "estimated_minutes": 15,
    })).json()["id"]

    await _transition(client, "steps", step_id, "ready")
    await _transition(client, "steps", step_id, "start")

    session_id = (await client.post(f"/api/v1/steps/{step_id}/sessions", json={
        "execution_mode": "focus", "session_started_at": _now(),
    })).json()["id"]
    await _transition(client, "sessions", session_id, "complete")

    witness_id = (await client.post(f"/api/v1/steps/{step_id}/witness", json={
        "witness_type": "passive", "witness_timestamp": _now(),
        "verification_class": "verified",
    })).json()["id"]
    await _transition(client, "witnesses", witness_id, "complete")

    outcome = (await client.post(f"/api/v1/steps/{step_id}/outcome", json={
        "witness_id": witness_id,
        "outcome_type": "completed",
        "outcome_timestamp": _now(),
    })).json()
    assert outcome["outcome_type"] == "completed"


# ── BehavioralEvent sensitivity enforcement ───────────────────────────────────

@pytest.mark.asyncio
async def test_behavioral_event_is_always_high_sensitive(client: AsyncClient) -> None:
    r = await client.post("/api/v1/behavioral-events", json={
        "behavioral_event_type": "urge_event",
        "event_timestamp": _now(),
        "user_declared_flag": True,
    })
    assert r.status_code == 201
    assert r.json()["sensitivity_class"] == "high_sensitive"
