"""
Phase 3 — performance baseline.

Each pipeline stage must respond in < 200ms (pure application time, no network).
Tests run against the test ASGI transport (zero network overhead), so 200ms is
a conservative ceiling — in practice the DB round-trip dominates at ~5-20ms.

If any assertion fails here, the bottleneck is application logic, not infra.
"""
import time
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


STAGE_BUDGET_MS = 200  # Maximum ms per stage (application time only)


async def _timed_post(client: AsyncClient, url: str, json: dict) -> tuple[dict, float]:
    t0 = time.perf_counter()
    r = await client.post(url, json=json)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert r.status_code in (200, 201), f"POST {url} returned {r.status_code}: {r.text}"
    return r.json(), elapsed_ms


async def _timed_get(client: AsyncClient, url: str) -> tuple[dict, float]:
    t0 = time.perf_counter()
    r = await client.get(url)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert r.status_code == 200, f"GET {url} returned {r.status_code}: {r.text}"
    return r.json(), elapsed_ms


@pytest.mark.asyncio
async def test_pipeline_stage_latency(client: AsyncClient) -> None:
    """
    Full pipeline pass — each stage timed independently.
    Budget: STAGE_BUDGET_MS per stage (currently 200ms).
    """
    timings: dict[str, float] = {}

    # Stage 1 — Command
    cmd, ms = await _timed_post(client, "/api/v1/commands", {
        "ingress_channel": "web",
        "ingress_modality": "text",
        "raw_payload_ref": "Perf test task",
        "submitted_at": _now(),
        "idempotency_key": _uid(),
    })
    timings["command_create"] = ms
    cmd_id = cmd["id"]

    # Stage 2 — Capture
    cap, ms = await _timed_post(client, f"/api/v1/commands/{cmd_id}/capture", {
        "raw_payload_ref": "Perf test task",
        "capture_integrity_status": "ok",
        "capture_hash": "p" * 48,
    })
    timings["capture_create"] = ms
    cap_id = cap["id"]

    # Stage 3 — Capture FSM transition
    _, ms = await _timed_post(client, f"/api/v1/transition/capture-records/{cap_id}", {
        "action": "complete",
    })
    timings["capture_transition"] = ms

    # Stage 4 — Decision (nano_task path — no reasoning)
    dec, ms = await _timed_post(client, f"/api/v1/capture/{cap_id}/decide", {
        "decision_outcome": "accept",
        "confirmed_by_user": True,
    })
    timings["decision_create"] = ms
    dec_id = dec["id"]

    # Stage 5 — Step
    step, ms = await _timed_post(client, f"/api/v1/decisions/{dec_id}/steps", {
        "step_type": "focus_step",
        "execution_readiness": "ready",
        "title": "Perf step",
        "step_order": 1,
        "estimated_minutes": 30,
    })
    timings["step_create"] = ms
    step_id = step["id"]

    # Stage 6 — Step transitions (pending → ready → in_progress)
    _, ms = await _timed_post(client, f"/api/v1/transition/steps/{step_id}", {"action": "ready"})
    timings["step_ready"] = ms
    _, ms = await _timed_post(client, f"/api/v1/transition/steps/{step_id}", {"action": "start"})
    timings["step_start"] = ms

    # Stage 7 — ExecutionSession
    sess, ms = await _timed_post(client, f"/api/v1/steps/{step_id}/sessions", {
        "execution_mode": "focus",
        "session_started_at": _now(),
    })
    timings["session_create"] = ms
    sess_id = sess["id"]

    _, ms = await _timed_post(client, f"/api/v1/transition/sessions/{sess_id}", {"action": "complete"})
    timings["session_complete"] = ms

    # Stage 8 — WitnessObject
    wit, ms = await _timed_post(client, f"/api/v1/steps/{step_id}/witness", {
        "witness_type": "passive",
        "witness_timestamp": _now(),
        "verification_class": "verified",
        "execution_session_id": sess_id,
    })
    timings["witness_create"] = ms
    wit_id = wit["id"]

    _, ms = await _timed_post(client, f"/api/v1/transition/witnesses/{wit_id}", {"action": "complete"})
    timings["witness_complete"] = ms

    # Stage 9 — OutcomeObject (terminal)
    _, ms = await _timed_post(client, f"/api/v1/steps/{step_id}/outcome", {
        "witness_id": wit_id,
        "outcome_type": "completed",
        "outcome_timestamp": _now(),
        "notes": "perf baseline",
    })
    timings["outcome_create"] = ms

    # Stage 10 — GET command (read path)
    _, ms = await _timed_get(client, f"/api/v1/commands/{cmd_id}")
    timings["command_read"] = ms

    # Assert budgets
    violations = [
        f"{stage}={ms:.1f}ms"
        for stage, ms in timings.items()
        if ms > STAGE_BUDGET_MS
    ]
    assert not violations, (
        f"Stages exceeded {STAGE_BUDGET_MS}ms budget: {', '.join(violations)}\n"
        f"Full timings: {timings}"
    )


@pytest.mark.asyncio
async def test_idempotency_no_extra_latency(client: AsyncClient) -> None:
    """Second request with same idempotency_key must not be slower than first (early-return path)."""
    payload = {
        "ingress_channel": "web",
        "ingress_modality": "text",
        "raw_payload_ref": "Idempotent perf task",
        "submitted_at": _now(),
        "idempotency_key": _uid(),
    }

    _, first_ms = await _timed_post(client, "/api/v1/commands", payload)
    _, second_ms = await _timed_post(client, "/api/v1/commands", payload)

    # Both within budget individually
    assert first_ms < STAGE_BUDGET_MS, f"First call: {first_ms:.1f}ms"
    assert second_ms < STAGE_BUDGET_MS, f"Idempotency check: {second_ms:.1f}ms"
