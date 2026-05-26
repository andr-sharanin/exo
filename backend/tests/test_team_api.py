"""
Tests for Team invitation API.

POST   /team/invitations         — create invitation (requires team tier)
GET    /team/invitations         — list invitations (requires team tier)
DELETE /team/invitations/{id}    — revoke pending invitation
GET    /team/invitations/lookup  — public lookup by token (no auth)
POST   /team/invitations/accept  — accept invitation by token (authenticated)
"""
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team_invitation import TeamInvitation
from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


def _patch_tier(tier: str = "team"):
    """Patch SubscriptionService.get_tier to return the given tier."""
    return patch(
        "app.api.v1.team.SubscriptionService",
        return_value=AsyncMock(get_tier=AsyncMock(return_value=tier)),
    )


def _patch_email():
    """Suppress actual email sending."""
    return patch("app.api.v1.team.send_email", new=AsyncMock(return_value=True))


def _patch_global_session(db: AsyncSession):
    """
    Patch AsyncSessionLocal (used for cross-tenant queries in accept/lookup)
    to yield the provided test session.
    """
    @asynccontextmanager
    async def _factory():
        yield db

    # The function does `from app.core.database import AsyncSessionLocal` inside itself,
    # so we patch the source module attribute.
    return patch("app.core.database.AsyncSessionLocal", return_value=_factory())


async def _insert_invite(
    db: AsyncSession,
    *,
    email: str = "guest@example.com",
    status: str = "pending",
    expires_at: datetime | None = None,
) -> TeamInvitation:
    import secrets
    inv = TeamInvitation(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        invited_by_user_id=TEST_USER_ID,
        email=email,
        status=status,
        token=secrets.token_urlsafe(48),
        expires_at=expires_at or datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(inv)
    await db.flush()
    return inv


# ── POST /team/invitations ────────────────────────────────────────────────────

class TestCreateInvitation:
    @pytest.mark.asyncio
    async def test_returns_201_on_success(self, client: AsyncClient) -> None:
        with _patch_tier(), _patch_email():
            r = await client.post(
                "/api/v1/team/invitations",
                json={"email": "newmember@example.com"},
            )
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "newmember@example.com"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_returns_402_when_not_team_tier(self, client: AsyncClient) -> None:
        with _patch_tier("free"):
            r = await client.post(
                "/api/v1/team/invitations",
                json={"email": "newmember@example.com"},
            )
        assert r.status_code == 402

    @pytest.mark.asyncio
    async def test_returns_409_on_duplicate_pending(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await _insert_invite(db, email="dup@example.com", status="pending")
        with _patch_tier(), _patch_email():
            r = await client.post(
                "/api/v1/team/invitations",
                json={"email": "dup@example.com"},
            )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_response_includes_id_and_expires_at(self, client: AsyncClient) -> None:
        with _patch_tier(), _patch_email():
            data = (await client.post(
                "/api/v1/team/invitations",
                json={"email": "fields@example.com"},
            )).json()
        assert "id" in data
        assert data["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_invalid_email_returns_422(self, client: AsyncClient) -> None:
        with _patch_tier():
            r = await client.post(
                "/api/v1/team/invitations",
                json={"email": "not-an-email"},
            )
        assert r.status_code == 422


# ── GET /team/invitations ─────────────────────────────────────────────────────

class TestListInvitations:
    @pytest.mark.asyncio
    async def test_returns_200_list(self, client: AsyncClient, db: AsyncSession) -> None:
        await _insert_invite(db, email="list1@example.com")
        with _patch_tier():
            r = await client.get("/api/v1/team/invitations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_returns_402_without_team_tier(self, client: AsyncClient) -> None:
        with _patch_tier("pro"):
            r = await client.get("/api/v1/team/invitations")
        assert r.status_code == 402

    @pytest.mark.asyncio
    async def test_includes_all_statuses(self, client: AsyncClient, db: AsyncSession) -> None:
        await _insert_invite(db, email="sta1@example.com", status="pending")
        await _insert_invite(db, email="sta2@example.com", status="accepted")
        with _patch_tier():
            data = (await client.get("/api/v1/team/invitations")).json()
        statuses = {i["status"] for i in data}
        assert "pending" in statuses


# ── DELETE /team/invitations/{id} ─────────────────────────────────────────────

class TestRevokeInvitation:
    @pytest.mark.asyncio
    async def test_returns_204(self, client: AsyncClient, db: AsyncSession) -> None:
        inv = await _insert_invite(db)
        r = await client.delete(f"/api/v1/team/invitations/{inv.id}")
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_status_set_to_revoked(self, client: AsyncClient, db: AsyncSession) -> None:
        inv = await _insert_invite(db)
        await client.delete(f"/api/v1/team/invitations/{inv.id}")
        await db.refresh(inv)
        assert inv.status == "revoked"

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_id(self, client: AsyncClient) -> None:
        r = await client.delete(f"/api/v1/team/invitations/{uuid.uuid4()}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_409_when_already_accepted(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        inv = await _insert_invite(db, status="accepted")
        r = await client.delete(f"/api/v1/team/invitations/{inv.id}")
        assert r.status_code == 409


# ── GET /team/invitations/lookup ──────────────────────────────────────────────

class TestLookupInvitation:
    @pytest.mark.asyncio
    async def test_returns_invite_info(self, client: AsyncClient, db: AsyncSession) -> None:
        inv = await _insert_invite(db, email="lookup@example.com")
        with _patch_global_session(db):
            r = await client.get(f"/api/v1/team/invitations/lookup?token={inv.token}")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "lookup@example.com"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_token(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        with _patch_global_session(db):
            r = await client.get("/api/v1/team/invitations/lookup?token=nonexistent_xyz_abc")
        assert r.status_code == 404
