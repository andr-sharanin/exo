"""
E2E tests for Phase 9: Stripe webhook handling.
Uses mock Stripe event payloads — no real Stripe calls.
Webhook signature verification is skipped in test mode (STRIPE_WEBHOOK_SECRET not set).
"""
import json
import uuid

import pytest
from httpx import AsyncClient


def _stripe_event(event_type: str, deposit_id: str | None = None) -> dict:
    return {
        "id": "evt_test_123",
        "type": event_type,
        "data": {
            "object": {
                "id": "pi_test_123",
                "status": "succeeded",
                "metadata": {"deposit_id": deposit_id or str(uuid.uuid4())},
            }
        },
    }


class TestStripeWebhook:
    async def test_webhook_endpoint_returns_200(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/stripe/webhook",
            content=json.dumps(_stripe_event("payment_intent.succeeded")),
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 200

    async def test_unknown_event_type_returns_200(
        self, client: AsyncClient
    ) -> None:
        r = await client.post(
            "/api/v1/stripe/webhook",
            content=json.dumps(_stripe_event("customer.created")),
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 200

    async def test_setup_intent_endpoint_returns_201(
        self, client: AsyncClient
    ) -> None:
        # Create a deposit first
        dep_data = (
            await client.post("/api/v1/deposits", json={
                "step_id": str(uuid.uuid4()),
                "amount_cents": 1000,
                "currency": "USD",
                "due_date": "2026-12-31",
            })
        ).json()
        dep_id = dep_data["id"]

        r = await client.post(f"/api/v1/deposits/{dep_id}/setup-intent")
        assert r.status_code in (200, 201)
        data = r.json()
        assert "client_secret" in data or "setup_intent_id" in data
