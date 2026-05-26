"""
Tests for StripeService and the Stripe webhook + deposit payment endpoints.

All Stripe API calls are monkeypatched — no real Stripe requests.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.stripe_service import StripeService, make_test_setup_intent
from tests.conftest import TEST_TENANT_ID, TEST_USER_ID


# ── make_test_setup_intent ────────────────────────────────────────────────────

def test_make_test_setup_intent_returns_pair():
    sid, secret = make_test_setup_intent(str(uuid.uuid4()))
    assert sid.startswith("seti_test_")
    assert "_secret_test" in secret


def test_make_test_setup_intent_deterministic():
    deposit_id = str(uuid.uuid4())
    sid1, _ = make_test_setup_intent(deposit_id)
    sid2, _ = make_test_setup_intent(deposit_id)
    assert sid1 == sid2


# ── StripeService unit tests (mocked stripe lib) ──────────────────────────────

def _make_svc():
    return StripeService(api_key="sk_test_fake")


@pytest.mark.asyncio
async def test_create_customer_calls_stripe():
    svc = _make_svc()
    fake_customer = MagicMock()
    fake_customer.id = "cus_test_123"

    with patch("stripe.Customer.create", return_value=fake_customer) as mock_create:
        cid = await svc.create_customer(user_id="user-uuid", email="test@example.com")

    assert cid == "cus_test_123"
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["metadata"]["user_id"] == "user-uuid"
    assert call_kwargs["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_create_customer_no_email_omits_field():
    svc = _make_svc()
    fake_customer = MagicMock()
    fake_customer.id = "cus_no_email"

    with patch("stripe.Customer.create", return_value=fake_customer) as mock_create:
        await svc.create_customer(user_id="u1", email="")

    # Should not have 'email' key when empty
    call_kwargs = mock_create.call_args.kwargs
    assert "email" not in call_kwargs


@pytest.mark.asyncio
async def test_create_setup_intent_returns_id_and_secret():
    svc = _make_svc()
    fake_intent = MagicMock()
    fake_intent.id = "seti_real_abc"
    fake_intent.client_secret = "seti_real_abc_secret_xyz"

    with patch("stripe.SetupIntent.create", return_value=fake_intent):
        intent_id, client_secret = await svc.create_setup_intent("cus_abc", "dep-123")

    assert intent_id == "seti_real_abc"
    assert client_secret == "seti_real_abc_secret_xyz"


@pytest.mark.asyncio
async def test_create_payment_intent_returns_id():
    svc = _make_svc()
    fake_intent = MagicMock()
    fake_intent.id = "pi_forfeited_abc"

    with patch("stripe.PaymentIntent.create", return_value=fake_intent):
        pi_id = await svc.create_payment_intent(
            customer_id="cus_abc",
            payment_method_id="pm_card_visa",
            amount_cents=5000,
            currency="USD",
            deposit_id="dep-uuid-1",
        )

    assert pi_id == "pi_forfeited_abc"


@pytest.mark.asyncio
async def test_create_payment_intent_includes_charity_transfer():
    svc = _make_svc()
    fake_intent = MagicMock()
    fake_intent.id = "pi_charity"

    with patch("stripe.PaymentIntent.create", return_value=fake_intent) as mock_pi:
        await svc.create_payment_intent(
            customer_id="cus_1",
            payment_method_id="pm_1",
            amount_cents=1000,
            currency="USD",
            deposit_id="dep-1",
            charity_account="acct_charity123",
        )

    kwargs = mock_pi.call_args.kwargs
    assert kwargs["transfer_data"] == {"destination": "acct_charity123"}


def test_construct_webhook_event_delegates_to_stripe():
    svc = _make_svc()
    fake_event = {"type": "payment_intent.succeeded", "data": {"object": {}}}

    with patch("stripe.Webhook.construct_event", return_value=fake_event) as mock_cw:
        result = svc.construct_webhook_event(b"body", "sig_header", "whsec_secret")

    assert result == fake_event
    mock_cw.assert_called_once_with(b"body", "sig_header", "whsec_secret")


# ── Webhook endpoint E2E ──────────────────────────────────────────────────────

def _webhook_body(event_type: str, deposit_id: str, extra: dict | None = None) -> dict:
    obj: dict = {"metadata": {"deposit_id": deposit_id}, "id": "evt_obj_1"}
    if extra:
        obj.update(extra)
    return {"type": event_type, "data": {"object": obj}}


class TestStripeWebhook:
    async def test_webhook_without_secret_accepts_json(
        self, client: AsyncClient
    ) -> None:
        body = _webhook_body("some.event", str(uuid.uuid4()))
        r = await client.post("/api/v1/stripe/webhook", json=body)
        assert r.status_code == 200
        assert r.json()["received"] is True

    async def test_webhook_unknown_deposit_returns_200(
        self, client: AsyncClient
    ) -> None:
        body = _webhook_body("payment_intent.succeeded", str(uuid.uuid4()))
        r = await client.post("/api/v1/stripe/webhook", json=body)
        assert r.status_code == 200

    async def test_webhook_setup_intent_succeeded_saves_payment_method(
        self, client: AsyncClient, db
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit
        from sqlalchemy import select

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=5000,
            currency="USD",
            status="held",
            due_date=date(2027, 1, 1),
        )
        db.add(dep)
        await db.flush()

        body = {
            "type": "setup_intent.succeeded",
            "data": {
                "object": {
                    "id": "seti_123",
                    "metadata": {"deposit_id": str(dep.id)},
                    "payment_method": "pm_card_visa_test",
                    "customer": "cus_test_001",
                }
            },
        }
        r = await client.post("/api/v1/stripe/webhook", json=body)
        assert r.status_code == 200

        await db.refresh(dep)
        assert dep.stripe_payment_method_id == "pm_card_visa_test"
        assert dep.stripe_customer_id == "cus_test_001"

    async def test_webhook_payment_intent_succeeded_marks_forfeited(
        self, client: AsyncClient, db
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=3000,
            currency="USD",
            status="held",
            due_date=date(2026, 1, 1),
            stripe_customer_id="cus_x",
            stripe_payment_method_id="pm_x",
        )
        db.add(dep)
        await db.flush()

        body = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_succeeded_test",
                    "metadata": {"deposit_id": str(dep.id)},
                }
            },
        }
        r = await client.post("/api/v1/stripe/webhook", json=body)
        assert r.status_code == 200

        await db.refresh(dep)
        assert dep.status == "forfeited"
        assert dep.forfeited_at is not None
        assert dep.stripe_payment_intent_id == "pi_succeeded_test"


# ── Setup-intent endpoint ─────────────────────────────────────────────────────

class TestSetupIntent:
    async def test_returns_test_mode_when_no_stripe_key(
        self, client: AsyncClient, db
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=1000,
            currency="USD",
            status="held",
            due_date=date(2027, 6, 1),
        )
        db.add(dep)
        await db.flush()

        with patch("app.api.v1.stripe_webhook._get_stripe_key", AsyncMock(return_value=None)):
            r = await client.post(f"/api/v1/deposits/{dep.id}/setup-intent")

        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "test"
        assert "client_secret" in data
        assert data["setup_intent_id"].startswith("seti_test_")

    async def test_setup_intent_with_real_key_calls_stripe(
        self, client: AsyncClient, db
    ) -> None:
        from app.models.commitment_deposit import CommitmentDeposit

        dep = CommitmentDeposit(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            step_id=uuid.uuid4(),
            amount_cents=2000,
            currency="USD",
            status="held",
            due_date=date(2027, 6, 1),
        )
        db.add(dep)
        await db.flush()

        mock_svc = MagicMock()
        mock_svc.create_customer = AsyncMock(return_value="cus_live_abc")
        mock_svc.create_setup_intent = AsyncMock(return_value=("seti_live_xyz", "seti_live_xyz_secret"))

        with (
            patch("app.api.v1.stripe_webhook._get_stripe_key", AsyncMock(return_value="sk_test_fake")),
            patch("app.api.v1.stripe_webhook.StripeService", return_value=mock_svc),
        ):
            r = await client.post(f"/api/v1/deposits/{dep.id}/setup-intent")

        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "live"
        assert data["setup_intent_id"] == "seti_live_xyz"
        assert data["customer_id"] == "cus_live_abc"
