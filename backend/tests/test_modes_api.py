"""E2E tests for Phase 4: /mode/* endpoints."""
import pytest
from httpx import AsyncClient


class TestModeSwitch:
    async def test_switch_creates_mode_record(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/mode/switch", json={"mode": "harmony"})
        assert r.status_code == 201
        data = r.json()
        assert data["mode"] == "harmony"
        assert data["previous_mode"] is None
        assert data["is_system_suggested"] is False
        assert "switched_at" in data
        assert "id" in data

    async def test_switch_tracks_previous_mode(self, client: AsyncClient) -> None:
        await client.post("/api/v1/mode/switch", json={"mode": "harmony"})
        r = await client.post("/api/v1/mode/switch", json={
            "mode": "recovery", "reason": "Feeling tired",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["mode"] == "recovery"
        assert data["previous_mode"] == "harmony"

    async def test_switch_stores_reason(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/mode/switch", json={
            "mode": "achiever",
            "reason": "Starting the week with high energy",
        })
        assert r.status_code == 201
        assert r.json()["switch_reason"] == "Starting the week with high energy"

    async def test_switch_without_reason(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/mode/switch", json={"mode": "clarity"})
        assert r.status_code == 201
        assert r.json()["switch_reason"] is None

    async def test_invalid_mode_rejected(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/mode/switch", json={"mode": "turbo_mode"})
        assert r.status_code == 422

    async def test_all_seven_modes_accepted(self, client: AsyncClient) -> None:
        modes = ["achiever", "harmony", "recovery", "learning", "clarity", "crisis", "creative"]
        for mode in modes:
            r = await client.post("/api/v1/mode/switch", json={"mode": mode})
            assert r.status_code == 201, f"Mode '{mode}' was incorrectly rejected"


class TestCurrentMode:
    async def test_no_mode_returns_404(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/mode/current")
        assert r.status_code == 404

    async def test_get_current_returns_latest(self, client: AsyncClient) -> None:
        await client.post("/api/v1/mode/switch", json={"mode": "achiever"})
        await client.post("/api/v1/mode/switch", json={"mode": "recovery"})
        r = await client.get("/api/v1/mode/current")
        assert r.status_code == 200
        assert r.json()["mode"] == "recovery"

    async def test_get_current_has_all_fields(self, client: AsyncClient) -> None:
        await client.post("/api/v1/mode/switch", json={"mode": "harmony", "reason": "test"})
        r = await client.get("/api/v1/mode/current")
        data = r.json()
        assert "id" in data
        assert "tenant_id" in data
        assert "user_id" in data
        assert "mode" in data
        assert "switched_at" in data
        assert "created_at" in data
