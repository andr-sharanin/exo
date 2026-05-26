"""
E2E tests for Governance API.

GET  /governance/policy          → 200 (default solo when no setting)
PUT  /governance/policy          → 200 upsert
POST /governance/records         → 201 (solo) | 201 (x2 pending_partner) | 400 (short reason)
GET  /governance/records         → 200 paginated list
POST /governance/records/{id}/approve → 200 | 403 (bad token) | 409 (already approved)
"""
import pytest
from httpx import AsyncClient


class TestGetPolicy:
    async def test_returns_200_with_default_solo_mode(
        self, client: AsyncClient
    ) -> None:
        r = await client.get("/api/v1/governance/policy")
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "solo"
        assert data["partner_email"] is None

    async def test_response_has_required_fields(
        self, client: AsyncClient
    ) -> None:
        data = (await client.get("/api/v1/governance/policy")).json()
        for field in ("id", "user_id", "mode", "partner_email", "created_at", "updated_at"):
            assert field in data, f"missing field: {field}"


class TestUpdatePolicy:
    async def test_set_solo_mode(self, client: AsyncClient) -> None:
        r = await client.put(
            "/api/v1/governance/policy",
            json={"mode": "solo", "partner_email": None},
        )
        assert r.status_code == 200
        assert r.json()["mode"] == "solo"

    async def test_set_x2_mode_with_email(self, client: AsyncClient) -> None:
        r = await client.put(
            "/api/v1/governance/policy",
            json={"mode": "x2", "partner_email": "partner@example.com"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "x2"
        assert data["partner_email"] == "partner@example.com"

    async def test_x2_mode_without_email_returns_400(
        self, client: AsyncClient
    ) -> None:
        r = await client.put(
            "/api/v1/governance/policy",
            json={"mode": "x2", "partner_email": None},
        )
        assert r.status_code == 400

    async def test_invalid_mode_returns_422(self, client: AsyncClient) -> None:
        r = await client.put(
            "/api/v1/governance/policy",
            json={"mode": "dictator", "partner_email": None},
        )
        assert r.status_code == 422

    async def test_update_is_persisted(self, client: AsyncClient) -> None:
        await client.put(
            "/api/v1/governance/policy",
            json={"mode": "solo", "partner_email": None},
        )
        data = (await client.get("/api/v1/governance/policy")).json()
        assert data["mode"] == "solo"


class TestCreateRecord:
    async def test_solo_mode_creates_self_approved_record(
        self, client: AsyncClient
    ) -> None:
        # Ensure solo mode
        await client.put(
            "/api/v1/governance/policy",
            json={"mode": "solo", "partner_email": None},
        )

        r = await client.post(
            "/api/v1/governance/records",
            json={
                "subject": "Delete old project branch",
                "reason": "This branch is three months stale and fully merged. Keeping it creates noise.",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "self_approved"
        assert data["approved_at"] is not None
        assert data["mode_at_time"] == "solo"

    async def test_x2_mode_creates_pending_record(
        self, client: AsyncClient
    ) -> None:
        await client.put(
            "/api/v1/governance/policy",
            json={"mode": "x2", "partner_email": "partner@example.com"},
        )
        r = await client.post(
            "/api/v1/governance/records",
            json={
                "subject": "Close savings account",
                "reason": "Account has been inactive for 2 years and has zero balance. Closing it simplifies finances.",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "pending_partner"
        assert data["approved_at"] is None

    async def test_reason_too_short_returns_422(
        self, client: AsyncClient
    ) -> None:
        await client.put(
            "/api/v1/governance/policy",
            json={"mode": "solo", "partner_email": None},
        )
        r = await client.post(
            "/api/v1/governance/records",
            json={"subject": "Something", "reason": "Too short"},
        )
        assert r.status_code == 422

    async def test_record_contains_subject(self, client: AsyncClient) -> None:
        await client.put(
            "/api/v1/governance/policy",
            json={"mode": "solo", "partner_email": None},
        )
        r = await client.post(
            "/api/v1/governance/records",
            json={
                "subject": "Archive old data pipeline",
                "reason": "Pipeline was replaced six months ago and no longer receives traffic.",
            },
        )
        assert r.json()["subject"] == "Archive old data pipeline"


class TestListRecords:
    async def test_returns_200_list(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/governance/records")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_created_record_appears_in_list(
        self, client: AsyncClient
    ) -> None:
        await client.put(
            "/api/v1/governance/policy",
            json={"mode": "solo", "partner_email": None},
        )
        await client.post(
            "/api/v1/governance/records",
            json={
                "subject": "Unique subject for list test",
                "reason": "Reason long enough to pass validation — this is at least twenty characters.",
            },
        )
        records = (await client.get("/api/v1/governance/records")).json()
        subjects = [r["subject"] for r in records]
        assert "Unique subject for list test" in subjects

    async def test_pagination_offset_works(self, client: AsyncClient) -> None:
        r_all = (await client.get("/api/v1/governance/records?limit=100&offset=0")).json()
        r_offset = (await client.get("/api/v1/governance/records?limit=100&offset=1")).json()
        assert len(r_all) >= len(r_offset)


class TestApproveRecord:
    async def _create_x2_record(self, client: AsyncClient) -> dict:
        await client.put(
            "/api/v1/governance/policy",
            json={"mode": "x2", "partner_email": "partner@example.com"},
        )
        r = await client.post(
            "/api/v1/governance/records",
            json={
                "subject": "Approval test record",
                "reason": "Long enough reason for the x2 approval flow test case.",
            },
        )
        return r.json()

    async def test_approve_with_valid_token_returns_200(
        self, client: AsyncClient, db
    ) -> None:
        # To get the token we need to query DB directly after creation
        record = await self._create_x2_record(client)
        record_id = record["id"]

        from sqlalchemy import select
        from app.models.governance import GovernanceRecord
        import uuid as _uuid

        result = await db.execute(
            select(GovernanceRecord).where(
                GovernanceRecord.id == _uuid.UUID(record_id)
            )
        )
        rec = result.scalar_one()
        token = rec.approval_token
        assert token is not None

        r = await client.post(
            f"/api/v1/governance/records/{record_id}/approve?token={token}"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "partner_approved"
        assert data["approved_at"] is not None

    async def test_approve_with_wrong_token_returns_403(
        self, client: AsyncClient
    ) -> None:
        record = await self._create_x2_record(client)
        r = await client.post(
            f"/api/v1/governance/records/{record['id']}/approve?token=wrong_token_123"
        )
        assert r.status_code == 403

    async def test_approve_already_approved_returns_409(
        self, client: AsyncClient, db
    ) -> None:
        record = await self._create_x2_record(client)
        record_id = record["id"]

        from sqlalchemy import select
        from app.models.governance import GovernanceRecord
        import uuid as _uuid

        result = await db.execute(
            select(GovernanceRecord).where(
                GovernanceRecord.id == _uuid.UUID(record_id)
            )
        )
        token = result.scalar_one().approval_token

        # First approval succeeds
        await client.post(
            f"/api/v1/governance/records/{record_id}/approve?token={token}"
        )
        # Second approval should conflict
        r = await client.post(
            f"/api/v1/governance/records/{record_id}/approve?token={token}"
        )
        assert r.status_code == 409

    async def test_approve_nonexistent_record_returns_404(
        self, client: AsyncClient
    ) -> None:
        fake_id = "00000000-0000-0000-0000-999999999999"
        r = await client.post(
            f"/api/v1/governance/records/{fake_id}/approve?token=anything"
        )
        assert r.status_code == 404
