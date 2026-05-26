"""
Subscriptions API — current tier info and Stripe Checkout session creation.

GET  /subscriptions/current     — return tier, status, limits for current user
POST /subscriptions/checkout    — create Stripe Checkout Session for upgrade
POST /subscriptions/portal      — create Stripe Customer Portal session (manage billing)
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.rls import TenantDB
from app.models.subscription import UserSubscription
from app.services.subscription_service import TIER_LIMITS, SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    current_period_end: datetime | None
    trial_end: datetime | None
    limits: dict

    class Config:
        from_attributes = True


class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro|team)$")
    success_url: str = Field(..., max_length=1024)
    cancel_url: str = Field(..., max_length=1024)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(db: TenantDB, user: CurrentUser) -> SubscriptionResponse:
    """Return the current user's tier, status, and applicable limits."""
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(user.user_id, user.tenant_id)
    tier = await svc.get_tier(user.user_id, user.tenant_id)

    return SubscriptionResponse(
        tier=tier,
        status=sub.status,
        current_period_end=sub.current_period_end,
        trial_end=sub.trial_end,
        limits=svc.limits(tier),
    )


@router.post("/checkout")
async def create_checkout_session(
    body: CheckoutRequest,
    db: TenantDB,
    user: CurrentUser,
) -> dict:
    """
    Create a Stripe Checkout Session for upgrading to Pro or Team.

    Returns {session_id, checkout_url} for use with Stripe.js redirectToCheckout.
    Requires stripe_secret_key and stripe_price_id_{plan} set in Admin Settings.
    """
    from app.services.config_service import ConfigService
    from app.services.stripe_service import StripeService

    config = ConfigService(db)
    stripe_key = await config.get("stripe_secret_key")
    if not stripe_key:
        stripe_key = ConfigService.get_from_env("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(501, "Stripe not configured — enter stripe_secret_key in Admin Settings")

    price_id = await config.get(f"stripe_price_id_{body.plan}")
    if not price_id:
        raise HTTPException(
            400,
            f"stripe_price_id_{body.plan} not configured in Admin Settings"
        )

    # Ensure customer exists
    svc = SubscriptionService(db)
    sub = await svc.get_or_create(user.user_id, user.tenant_id)

    stripe_svc = StripeService(stripe_key)

    if not sub.stripe_customer_id:
        customer_id = await stripe_svc.create_customer(
            user_id=str(user.user_id),
            email=user.email or "",
        )
        sub.stripe_customer_id = customer_id
        await db.flush()
    else:
        customer_id = sub.stripe_customer_id

    # Create Checkout Session
    import stripe
    stripe.api_key = stripe_key

    import asyncio, functools
    session = await asyncio.get_event_loop().run_in_executor(
        None,
        functools.partial(
            stripe.checkout.Session.create,
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            metadata={"user_id": str(user.user_id), "tenant_id": str(user.tenant_id)},
        ),
    )
    return {"session_id": session.id, "checkout_url": session.url}


@router.post("/portal")
async def create_portal_session(
    db: TenantDB,
    user: CurrentUser,
    return_url: str = "/settings/subscription",
) -> dict:
    """Create a Stripe Customer Portal session for managing billing."""
    from app.services.config_service import ConfigService

    config = ConfigService(db)
    stripe_key = await config.get("stripe_secret_key")
    if not stripe_key:
        stripe_key = ConfigService.get_from_env("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(501, "Stripe not configured")

    svc = SubscriptionService(db)
    sub = await svc.get_or_create(user.user_id, user.tenant_id)

    if not sub.stripe_customer_id:
        raise HTTPException(400, "No Stripe customer linked to this account")

    import stripe, asyncio, functools
    stripe.api_key = stripe_key
    portal = await asyncio.get_event_loop().run_in_executor(
        None,
        functools.partial(
            stripe.billing_portal.Session.create,
            customer=sub.stripe_customer_id,
            return_url=return_url,
        ),
    )
    return {"portal_url": portal.url}
