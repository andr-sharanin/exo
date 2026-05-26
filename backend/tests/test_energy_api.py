"""
E2E tests for Phase 4: /energy/* endpoints and BehavioralPolicy integration.
Uses the shared `client` fixture from conftest (rollback after each test).
"""
import pytest
from httpx import AsyncClient


class TestEnergyCheckin:
    async def test_checkin_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 4, "mood": 4, "energy_level": 4,
        })
        assert r.status_code == 201

    async def test_checkin_perfect_scores_sufficient(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 5, "mood": 5, "energy_level": 5,
        })
        assert r.status_code == 201
        data = r.json()
        # Late-night penalty can reduce from 100 to 90 — state is the reliable assertion
        assert data["score"] >= 90
        assert data["state"] == "sufficient"
        assert data["is_override"] is False
        assert "valid_until" in data
        assert "id" in data

    async def test_checkin_minimum_scores_critical(self, client: AsyncClient) -> None:
        # Base score 20; with any time-of-day adjustment stays <= 28 → always critical
        r = await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 1, "mood": 1, "energy_level": 1,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["state"] == "critical"
        assert data["score"] <= 40

    async def test_checkin_suggests_crisis_on_critical(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 1, "mood": 1, "energy_level": 1,
        })
        data = r.json()
        assert data["suggested_mode"] == "crisis"

    async def test_checkin_sufficient_no_suggested_mode(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 5, "mood": 5, "energy_level": 5,
        })
        data = r.json()
        assert data["suggested_mode"] is None

    async def test_checkin_validates_range_above_5(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 6, "mood": 3, "energy_level": 3,
        })
        assert r.status_code == 422

    async def test_checkin_validates_range_below_1(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 0, "mood": 3, "energy_level": 3,
        })
        assert r.status_code == 422

    async def test_checkin_with_optional_note(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 4, "mood": 4, "energy_level": 4,
            "note": "Feeling refreshed after the weekend",
        })
        assert r.status_code == 201


class TestEnergyScore:
    async def test_get_score_no_data_returns_404(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/energy/score")
        assert r.status_code == 404

    async def test_get_score_returns_latest_after_checkin(self, client: AsyncClient) -> None:
        await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 4, "mood": 4, "energy_level": 4,
        })
        r = await client.get("/api/v1/energy/score")
        assert r.status_code == 200
        data = r.json()
        assert "score" in data
        assert "state" in data
        assert "valid_until" in data

    async def test_get_score_suggested_mode_is_none(self, client: AsyncClient) -> None:
        await client.post("/api/v1/energy/checkin", json={
            "sleep_quality": 4, "mood": 4, "energy_level": 4,
        })
        r = await client.get("/api/v1/energy/score")
        # GET never computes a suggestion — only create endpoints do
        assert r.json()["suggested_mode"] is None


class TestEnergyOverride:
    async def test_override_sets_exact_score(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/override", json={
            "score": 85, "reason": "Just got back from vacation",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["score"] == 85
        assert data["state"] == "sufficient"
        assert data["is_override"] is True

    async def test_override_critical_suggests_crisis(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/override", json={
            "score": 15, "reason": "Exhausted today",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["state"] == "critical"
        assert data["suggested_mode"] == "crisis"

    async def test_override_validates_range_above_100(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/override", json={
            "score": 150, "reason": "test",
        })
        assert r.status_code == 422

    async def test_override_validates_range_below_0(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/override", json={
            "score": -1, "reason": "test",
        })
        assert r.status_code == 422

    async def test_override_requires_reason(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/energy/override", json={"score": 70})
        assert r.status_code == 422


class TestBehavioralEventPolicy:
    async def test_urge_event_includes_interrupt_policy(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/behavioral-events", json={
            "behavioral_event_type": "urge_event",
            "event_timestamp": "2026-04-30T10:00:00Z",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["policy_response"] is not None
        assert data["policy_response"]["action"] == "interrupt"
        assert data["policy_response"]["delay_minutes"] > 0
        assert data["policy_response"]["reflection_prompt"]

    async def test_recovery_event_reinforces(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/behavioral-events", json={
            "behavioral_event_type": "recovery_event",
            "event_timestamp": "2026-04-30T10:00:00Z",
        })
        assert r.status_code == 201
        assert r.json()["policy_response"]["action"] == "reinforce"

    async def test_lapse_event_acknowledges(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/behavioral-events", json={
            "behavioral_event_type": "lapse_event",
            "event_timestamp": "2026-04-30T10:00:00Z",
        })
        assert r.status_code == 201
        assert r.json()["policy_response"]["action"] == "acknowledge"

    async def test_risk_window_alerts(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/behavioral-events", json={
            "behavioral_event_type": "risk_window",
            "event_timestamp": "2026-04-30T10:00:00Z",
        })
        assert r.status_code == 201
        assert r.json()["policy_response"]["action"] == "alert"

    async def test_get_event_policy_response_is_none(self, client: AsyncClient) -> None:
        create_r = await client.post("/api/v1/behavioral-events", json={
            "behavioral_event_type": "urge_event",
            "event_timestamp": "2026-04-30T10:00:00Z",
        })
        event_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/behavioral-events/{event_id}")
        assert r.status_code == 200
        # GET does not re-compute policy — field is None
        assert r.json()["policy_response"] is None
