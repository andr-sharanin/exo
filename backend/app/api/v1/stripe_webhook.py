"""
Stripe Integration — full payment lifecycle for commitment deposits.

Endpoints:
  POST /stripe/webhook              — receive & verify Stripe events
  POST /deposits/{id}/setup-intent  — save payment method (step 1)
  POST /deposits/{id}/pay           — charge deposit immediately (manual forfeit)

Webhook events handled:
  setup_intent.succeeded    → save stripe_payment_method_id + stripe_customer_id
  payment_intent.succeeded  → mark deposit forfeited + record forfeited_at
  payment_intent.payment_failed → log; deposit remains "held" for retry

Auto-forfeit runs daily via ARQ cron (forfeit_overdue_deposits in cron_tasks.py).
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.commitment_deposit import CommitmentDeposit
from app.repositories.deposit_repos import CommitmentDepositRepo
from app.services.config_service import ConfigService
from app.services.stripe_service import StripeService, make_test_setup_intent

router = APIRouter(tags=["stripe"])
log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_stripe_key(db) -> str | None:
    """Return Stripe secret key from ConfigService (DB → env → None)."""
    svc = ConfigService(db)
    key = await svc.get("stripe_secret_key")
    if not key:
        key = ConfigService.get_from_env("STRIPE_SECRET_KEY")
    return key or None


async def _find_deposit_by_metadata(db, deposit_id_str: str) -> CommitmentDeposit | None:
    """Load deposit ignoring RLS (webhook doesn't have a tenant context)."""
    try:
        deposit_id = uuid.UUID(deposit_id_str)
    except ValueError:
        return None
    result = await db.execute(
        select(CommitmentDeposit).where(CommitmentDeposit.id == deposit_id)
    )
    return result.scalar_one_or_none()


# ── Webhook ────────────────────────────────────────────────────────────────────

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: TenantDB) -> dict:
    """Receive Stripe webhook events with HMAC signature verification."""
    body = await request.body()

    # ── Signature verification ─────────────────────────────────────────────
    webhook_secret = ConfigService.get_from_env("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        # Also try DB (in case it was set via Admin UI)
        from app.services.config_service import ConfigService as _CS
        webhook_secret = await _CS(db).get("stripe_webhook_secret")

    if webhook_secret:
        stripe_sig = request.headers.get("stripe-signature", "")
        if not stripe_sig:
            raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
        stripe_key = await _get_stripe_key(db)
        if stripe_key:
            svc = StripeService(stripe_key)
            try:
                event = svc.construct_webhook_event(body, stripe_sig, webhook_secret)
            except Exception as exc:
                log.warning("Stripe webhook signature verification failed: %s", exc)
                raise HTTPException(status_code=400, detail="Invalid Stripe signature")
        else:
            # No key yet — parse without verification (dev/test mode)
            import json
            try:
                event = json.loads(body)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON")
    else:
        import json
        try:
            event = json.loads(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    # ── Event dispatch ─────────────────────────────────────────────────────
    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    deposit_id_str = obj.get("metadata", {}).get("deposit_id", "")

    # ── Subscription events ────────────────────────────────────────────────
    _SUBSCRIPTION_EVENTS = {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
    }
    if event_type in _SUBSCRIPTION_EVENTS:
        from app.services.subscription_service import SubscriptionService
        sub_svc = SubscriptionService(db)
        try:
            await sub_svc.apply_stripe_event(event_type, obj)
            await db.commit()
        except Exception as exc:
            log.error("stripe_webhook: failed to apply subscription event %s: %s", event_type, exc)
        return {"received": True}

    if not deposit_id_str:
        return {"received": True}

    deposit = await _find_deposit_by_metadata(db, deposit_id_str)
    if deposit is None:
        log.warning("stripe_webhook: deposit %s not found for event %s", deposit_id_str, event_type)
        return {"received": True}

    now = datetime.now(timezone.utc)

    if event_type == "setup_intent.succeeded":
        # Card saved — extract payment_method and customer
        pm_id = obj.get("payment_method")
        customer_id = obj.get("customer")
        if pm_id:
            deposit.stripe_payment_method_id = pm_id
        if customer_id:
            deposit.stripe_customer_id = customer_id
        # Store the setup intent id if not already set
        if not deposit.stripe_setup_intent_id:
            deposit.stripe_setup_intent_id = obj.get("id")
        await db.flush()
        log.info("stripe_webhook: payment method saved for deposit %s", deposit_id_str)

    elif event_type == "payment_intent.succeeded":
        if deposit.status == "held":
            deposit.status = "forfeited"
            deposit.forfeited_at = now
            deposit.stripe_payment_intent_id = obj.get("id", deposit.stripe_payment_intent_id)
            await db.flush()
            log.info("stripe_webhook: deposit %s forfeited via PaymentIntent", deposit_id_str)

    elif event_type == "payment_intent.payment_failed":
        log.warning(
            "stripe_webhook: PaymentIntent failed for deposit %s — error: %s",
            deposit_id_str,
            obj.get("last_payment_error", {}).get("message", "unknown"),
        )
        # Deposit remains "held"; ops team can retry or resolve manually

    return {"received": True}


# ── Setup Intent (step 1: save card) ──────────────────────────────────────────

@router.post("/deposits/{deposit_id}/setup-intent")
async def create_setup_intent(
    deposit_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> dict:
    """
    Create a Stripe SetupIntent so the user can save their card without charging.

    Returns client_secret for use with Stripe.js.
    After the card is saved Stripe fires setup_intent.succeeded webhook which
    stores stripe_payment_method_id on the deposit.
    """
    repo = CommitmentDepositRepo(db)
    deposit = await repo.get_or_404(deposit_id, user.tenant_id)

    stripe_key = await _get_stripe_key(db)

    if not stripe_key:
        # Test mode: return synthetic data so frontend can exercise the flow
        intent_id, client_secret = make_test_setup_intent(str(deposit_id))
        deposit.stripe_setup_intent_id = intent_id
        await db.flush()
        return {
            "setup_intent_id": intent_id,
            "client_secret": client_secret,
            "mode": "test",
        }

    svc = StripeService(stripe_key)

    # Reuse existing customer if already stored on this deposit
    if deposit.stripe_customer_id:
        customer_id = deposit.stripe_customer_id
    else:
        customer_id = await svc.create_customer(
            user_id=str(user.user_id),
            email=user.email or "",
        )
        deposit.stripe_customer_id = customer_id

    intent_id, client_secret = await svc.create_setup_intent(customer_id, str(deposit_id))
    deposit.stripe_setup_intent_id = intent_id
    await db.flush()

    return {
        "setup_intent_id": intent_id,
        "client_secret": client_secret,
        "customer_id": customer_id,
        "mode": "live",
    }


# ── Manual pay (immediate forfeit charge) ─────────────────────────────────────

@router.post("/deposits/{deposit_id}/pay")
async def charge_deposit(
    deposit_id: uuid.UUID,
    db: TenantDB,
    user: CurrentUser,
) -> dict:
    """
    Immediately charge the saved card for a deposit (manual forfeit trigger).

    Requires that setup-intent has been completed first (stripe_payment_method_id set).
    Normally auto-forfeit runs via ARQ daily cron; this endpoint is for manual use.
    """
    repo = CommitmentDepositRepo(db)
    deposit = await repo.get_or_404(deposit_id, user.tenant_id)

    if deposit.status != "held":
        raise HTTPException(409, f"Deposit is already '{deposit.status}' — cannot charge")

    if not deposit.stripe_payment_method_id:
        raise HTTPException(
            400,
            "No payment method saved for this deposit. "
            "Complete the setup-intent flow first."
        )

    stripe_key = await _get_stripe_key(db)
    if not stripe_key:
        raise HTTPException(501, "Stripe not configured — enter stripe_secret_key in Admin Settings")

    charity_account = await ConfigService(db).get("stripe_charity_account")
    svc = StripeService(stripe_key)

    payment_intent_id = await svc.create_payment_intent(
        customer_id=deposit.stripe_customer_id or "",
        payment_method_id=deposit.stripe_payment_method_id,
        amount_cents=deposit.amount_cents,
        currency=deposit.currency,
        deposit_id=str(deposit_id),
        charity_account=charity_account or None,
    )

    deposit.stripe_payment_intent_id = payment_intent_id
    await db.flush()

    return {
        "payment_intent_id": payment_intent_id,
        "status": "charge_initiated",
        "message": "PaymentIntent created. Deposit will be marked forfeited via webhook on success.",
    }
