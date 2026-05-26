"""
E2E tests for Phase 8: /deposits endpoints.
No Stripe — mock escrow model, status transitions only.
"""
import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


def _deposit_body(
    days_until_due: int = 7,
    amount_cents: int = 500,
) -> dict:
    return {
        "step_id": str(uuid.uuid4()),
        "amount_cents": amount_cents,
        "currency": "USD",
        "due_date": (date.today() + timedelta(days=days_until_due)).isoformat(),
    }


class TestCreateDeposit:
    async def test_create_deposit_returns_201(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/deposits", json=_deposit_body())
        assert r.status_code == 201

    async def test_create_deposit_has_required_fields(
        self, client: AsyncClient
    ) -> None:
        data = (await client.post("/api/v1/deposits", json=_deposit_body())).json()
        assert "id" in data
        assert "step_id" in data
        assert "amount_cents" in data
        assert "currency" in data
        assert "status" in data
        assert "due_date" in data
        assert data["status"] == "held"

    async def test_amount_must_be_positive(self, client: AsyncClient) -> None:
        r = await client.post("/api/v1/deposits", json=_deposit_body(amount_cents=0))
        assert r.status_code == 422

    async def test_due_date_must_be_future(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/deposits",
            json=_deposit_body(days_until_due=-1),
        )
        assert r.status_code == 422


class TestListDeposits:
    async def test_list_deposits_returns_200(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/deposits")
        assert r.status_code == 200

    async def test_created_deposit_appears_in_list(
        self, client: AsyncClient
    ) -> None:
        dep_id = (
            await client.post("/api/v1/deposits", json=_deposit_body())
        ).json()["id"]
        data = (await client.get("/api/v1/deposits")).json()
        ids = [d["id"] for d in data]
        assert dep_id in ids


class TestReleaseDeposit:
    async def test_release_returns_200(self, client: AsyncClient) -> None:
        dep_id = (
            await client.post("/api/v1/deposits", json=_deposit_body())
        ).json()["id"]
        r = await client.post(f"/api/v1/deposits/{dep_id}/release")
        assert r.status_code == 200

    async def test_release_changes_status_to_released(
        self, client: AsyncClient
    ) -> None:
        dep_id = (
            await client.post("/api/v1/deposits", json=_deposit_body())
        ).json()["id"]
        data = (
            await client.post(f"/api/v1/deposits/{dep_id}/release")
        ).json()
        assert data["status"] == "released"

    async def test_double_release_returns_409(self, client: AsyncClient) -> None:
        dep_id = (
            await client.post("/api/v1/deposits", json=_deposit_body())
        ).json()["id"]
        await client.post(f"/api/v1/deposits/{dep_id}/release")
        r = await client.post(f"/api/v1/deposits/{dep_id}/release")
        assert r.status_code == 409


class TestForfeitDeposit:
    async def test_forfeit_returns_200(self, client: AsyncClient) -> None:
        dep_id = (
            await client.post("/api/v1/deposits", json=_deposit_body())
        ).json()["id"]
        r = await client.post(f"/api/v1/deposits/{dep_id}/forfeit")
        assert r.status_code == 200

    async def test_forfeit_changes_status_to_forfeited(
        self, client: AsyncClient
    ) -> None:
        dep_id = (
            await client.post("/api/v1/deposits", json=_deposit_body())
        ).json()["id"]
        data = (
            await client.post(f"/api/v1/deposits/{dep_id}/forfeit")
        ).json()
        assert data["status"] == "forfeited"

    async def test_forfeit_already_released_returns_409(
        self, client: AsyncClient
    ) -> None:
        dep_id = (
            await client.post("/api/v1/deposits", json=_deposit_body())
        ).json()["id"]
        await client.post(f"/api/v1/deposits/{dep_id}/release")
        r = await client.post(f"/api/v1/deposits/{dep_id}/forfeit")
        assert r.status_code == 409
