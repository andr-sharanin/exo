"""
Unit tests for Phase 8: CommitmentDepositService.
Pure function tests — no database.
"""
from datetime import date, timedelta

import pytest

from app.services.deposit import CommitmentDepositService


class TestShouldForfeit:
    def test_past_due_date_should_forfeit(self) -> None:
        yesterday = date.today() - timedelta(days=1)
        assert CommitmentDepositService.should_forfeit(yesterday) is True

    def test_due_today_should_not_forfeit(self) -> None:
        assert CommitmentDepositService.should_forfeit(date.today()) is False

    def test_future_due_date_should_not_forfeit(self) -> None:
        tomorrow = date.today() + timedelta(days=1)
        assert CommitmentDepositService.should_forfeit(tomorrow) is False

    def test_far_past_should_forfeit(self) -> None:
        last_year = date.today() - timedelta(days=365)
        assert CommitmentDepositService.should_forfeit(last_year) is True


class TestAmountDisplay:
    def test_cents_to_display_usd(self) -> None:
        assert CommitmentDepositService.cents_to_display(1000, "USD") == "10.00 USD"

    def test_cents_to_display_rounds_correctly(self) -> None:
        assert CommitmentDepositService.cents_to_display(99, "USD") == "0.99 USD"

    def test_cents_to_display_zero(self) -> None:
        assert CommitmentDepositService.cents_to_display(0, "USD") == "0.00 USD"

    def test_cents_to_display_large_amount(self) -> None:
        assert CommitmentDepositService.cents_to_display(100000, "EUR") == "1000.00 EUR"
