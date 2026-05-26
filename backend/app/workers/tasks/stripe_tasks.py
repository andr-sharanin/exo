"""
ARQ tasks for Stripe deposit lifecycle.

charge_deposit_task      — charge a single deposit (called per-deposit from cron)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)


async def charge_deposit_task(ctx: dict, deposit_id: str) -> None:
    """
    Create a PaymentIntent to forfeit a single overdue deposit.

    Called from forfeit_overdue_deposits cron for each eligible deposit.
    On success Stripe fires payment_intent.succeeded webhook which sets
    deposit.status = "forfeited".
    """
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.commitment_deposit import CommitmentDeposit
    from app.services.config_service import ConfigService
    from app.services.stripe_service import StripeService

    import uuid
    try:
        dep_uuid = uuid.UUID(deposit_id)
    except ValueError:
        log.error("charge_deposit_task: invalid deposit_id %s", deposit_id)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CommitmentDeposit).where(CommitmentDeposit.id == dep_uuid)
        )
        deposit = result.scalar_one_or_none()

        if not deposit:
            log.warning("charge_deposit_task: deposit %s not found", deposit_id)
            return

        if deposit.status != "held":
            log.info("charge_deposit_task: deposit %s already %s — skipping", deposit_id, deposit.status)
            return

        if not deposit.stripe_payment_method_id or not deposit.stripe_customer_id:
            log.warning(
                "charge_deposit_task: deposit %s has no payment method — cannot charge",
                deposit_id,
            )
            return

        config = ConfigService(db)
        stripe_key = await config.get("stripe_secret_key")
        if not stripe_key:
            stripe_key = ConfigService.get_from_env("STRIPE_SECRET_KEY")
        if not stripe_key:
            log.error("charge_deposit_task: no Stripe key configured — deposit %s not charged", deposit_id)
            return

        charity_account = await config.get("stripe_charity_account")
        svc = StripeService(stripe_key)

        try:
            payment_intent_id = await svc.create_payment_intent(
                customer_id=deposit.stripe_customer_id,
                payment_method_id=deposit.stripe_payment_method_id,
                amount_cents=deposit.amount_cents,
                currency=deposit.currency,
                deposit_id=deposit_id,
                charity_account=charity_account or None,
            )
            deposit.stripe_payment_intent_id = payment_intent_id
            await db.flush()
            await db.commit()
            log.info(
                "charge_deposit_task: PaymentIntent %s created for deposit %s",
                payment_intent_id,
                deposit_id,
            )
        except Exception as exc:
            log.error("charge_deposit_task: Stripe error for deposit %s: %s", deposit_id, exc)
