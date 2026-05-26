"""
StripeService — all Stripe API interactions for commitment deposits.

Responsibilities:
  - create_customer(): one Stripe Customer per user, id stored on deposit
  - create_setup_intent(): save card without charging (for deposit commitment)
  - create_payment_intent(): charge the saved card (on forfeit)
  - construct_webhook_event(): HMAC-verified webhook parsing

All Stripe calls are synchronous (stripe lib) and are run in a thread pool
via asyncio.get_event_loop().run_in_executor() to avoid blocking the event loop.

Usage (inject api_key from ConfigService, not from .env):
    svc = StripeService(api_key)
    customer_id = await svc.create_customer(user_id="uuid-...", email="user@example.com")
    setup_id, client_secret = await svc.create_setup_intent(customer_id, deposit_id)
"""
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any

log = logging.getLogger(__name__)

_TEST_MODE_PREFIX = "seti_test_"


def _run_sync(fn, *args, **kwargs):
    """Run a synchronous function in the default thread executor."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))


class StripeService:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _import(self):
        import stripe
        stripe.api_key = self._api_key
        return stripe

    # ── Customer ──────────────────────────────────────────────────────────────

    async def create_customer(self, user_id: str, email: str = "") -> str:
        """Create a Stripe Customer and return its id.

        Idempotent via metadata lookup is intentionally NOT done here — the caller
        stores the customer_id on the deposit and reuses it on the next setup intent.
        """
        stripe = self._import()
        customer = await _run_sync(
            stripe.Customer.create,
            metadata={"user_id": user_id},
            **{"email": email} if email else {},
        )
        return customer.id

    # ── SetupIntent ───────────────────────────────────────────────────────────

    async def create_setup_intent(
        self, customer_id: str, deposit_id: str
    ) -> tuple[str, str]:
        """Create a SetupIntent attached to customer.

        Returns (setup_intent_id, client_secret).
        Frontend uses client_secret with Stripe.js to collect the card.
        After the card is collected Stripe sends setup_intent.succeeded webhook.
        """
        stripe = self._import()
        intent = await _run_sync(
            stripe.SetupIntent.create,
            customer=customer_id,
            payment_method_types=["card"],
            metadata={"deposit_id": deposit_id},
        )
        return intent.id, intent.client_secret

    # ── PaymentIntent (forfeit charge) ────────────────────────────────────────

    async def create_payment_intent(
        self,
        customer_id: str,
        payment_method_id: str,
        amount_cents: int,
        currency: str,
        deposit_id: str,
        charity_account: str | None = None,
    ) -> str:
        """Charge the saved card off-session (forfeit).

        Returns payment_intent_id.
        Stripe sends payment_intent.succeeded webhook on success.
        If charity_account is set, adds a transfer_data so Stripe routes the funds.
        """
        stripe = self._import()
        kwargs: dict[str, Any] = {
            "amount": amount_cents,
            "currency": currency.lower(),
            "customer": customer_id,
            "payment_method": payment_method_id,
            "confirm": True,
            "off_session": True,
            "metadata": {"deposit_id": deposit_id},
        }
        if charity_account:
            kwargs["transfer_data"] = {"destination": charity_account}

        intent = await _run_sync(stripe.PaymentIntent.create, **kwargs)
        return intent.id

    # ── Webhook verification ──────────────────────────────────────────────────

    def construct_webhook_event(
        self, body: bytes, sig_header: str, secret: str
    ) -> dict:
        """Verify Stripe-Signature and return parsed event dict.

        Raises stripe.error.SignatureVerificationError on invalid signature.
        This is pure HMAC — synchronous, no I/O needed.
        """
        stripe = self._import()
        return stripe.Webhook.construct_event(body, sig_header, secret)


# ── Test-mode helpers ─────────────────────────────────────────────────────────

def make_test_setup_intent(deposit_id: str) -> tuple[str, str]:
    """Returns synthetic (setup_intent_id, client_secret) when no Stripe key is set."""
    intent_id = f"seti_test_{deposit_id.replace('-', '')[:24]}"
    return intent_id, f"{intent_id}_secret_test"
