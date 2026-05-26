"""
CommitmentDepositService — pure logic for commitment deposit mechanics.

Loss aversion: user pledges a deposit on a step/goal.
  - Completed on time → status: released (returned to user)
  - Missed deadline  → status: forfeited (to charity/fund)

No Stripe calls here — integration layer handles payment intents separately.
"""
from datetime import date


class CommitmentDepositService:
    @staticmethod
    def should_forfeit(due_date: date) -> bool:
        """Return True if the deposit deadline has passed (due_date < today)."""
        return due_date < date.today()

    @staticmethod
    def cents_to_display(amount_cents: int, currency: str) -> str:
        """Format amount in cents to human-readable string."""
        return f"{amount_cents / 100:.2f} {currency}"
