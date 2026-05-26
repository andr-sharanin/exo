"""
Unit tests for Phase 7: SecretaryService.
Written FIRST (TDD). Pure function tests — no database, no AI calls.
"""
import pytest

from app.services.secretary import SecretaryService


def _step(
    step_type: str = "focus_step",
    execution_readiness: str = "ready",
    estimated_minutes: int | None = 45,
    title: str = "Test step",
    step_id: str = "00000000-0000-0000-0000-000000000001",
) -> dict:
    return {
        "id": step_id,
        "title": title,
        "step_type": step_type,
        "execution_readiness": execution_readiness,
        "estimated_minutes": estimated_minutes,
    }


class TestDeriveEnergyCost:
    def test_none_minutes_is_low(self) -> None:
        assert SecretaryService.derive_energy_cost(None) == "low"

    def test_25_minutes_is_low(self) -> None:
        assert SecretaryService.derive_energy_cost(25) == "low"

    def test_26_minutes_is_medium(self) -> None:
        assert SecretaryService.derive_energy_cost(26) == "medium"

    def test_60_minutes_is_medium(self) -> None:
        assert SecretaryService.derive_energy_cost(60) == "medium"

    def test_61_minutes_is_high(self) -> None:
        assert SecretaryService.derive_energy_cost(61) == "high"


class TestStepScoring:
    def test_rescue_entry_has_highest_base_score(self) -> None:
        rescue = SecretaryService.score_step(
            _step("rescue_entry_step"), "sufficient", "harmony"
        )
        focus = SecretaryService.score_step(
            _step("focus_step"), "sufficient", "harmony"
        )
        background = SecretaryService.score_step(
            _step("background_step"), "sufficient", "harmony"
        )
        assert rescue > focus > background

    def test_blocked_step_gets_large_negative_score(self) -> None:
        score = SecretaryService.score_step(
            _step(execution_readiness="blocked"), "sufficient", "harmony"
        )
        assert score < 0

    def test_high_cost_boosted_when_energy_sufficient(self) -> None:
        high_cost = SecretaryService.score_step(
            _step(estimated_minutes=90), "sufficient", "harmony"
        )
        low_cost = SecretaryService.score_step(
            _step(estimated_minutes=15), "sufficient", "harmony"
        )
        assert high_cost > low_cost

    def test_high_cost_penalized_when_energy_critical(self) -> None:
        score_sufficient = SecretaryService.score_step(
            _step(estimated_minutes=90), "sufficient", "harmony"
        )
        score_critical = SecretaryService.score_step(
            _step(estimated_minutes=90), "critical", "harmony"
        )
        assert score_critical < score_sufficient

    def test_low_cost_boosted_when_energy_critical(self) -> None:
        score_sufficient = SecretaryService.score_step(
            _step(estimated_minutes=15), "sufficient", "harmony"
        )
        score_critical = SecretaryService.score_step(
            _step(estimated_minutes=15), "critical", "harmony"
        )
        assert score_critical > score_sufficient

    def test_achiever_mode_boosts_focus_step(self) -> None:
        achiever = SecretaryService.score_step(
            _step("focus_step"), "sufficient", "achiever"
        )
        harmony = SecretaryService.score_step(
            _step("focus_step"), "sufficient", "harmony"
        )
        assert achiever > harmony

    def test_recovery_mode_penalizes_focus_step(self) -> None:
        recovery = SecretaryService.score_step(
            _step("focus_step"), "sufficient", "recovery"
        )
        harmony = SecretaryService.score_step(
            _step("focus_step"), "sufficient", "harmony"
        )
        assert recovery < harmony

    def test_crisis_mode_strongly_boosts_rescue_entry(self) -> None:
        crisis = SecretaryService.score_step(
            _step("rescue_entry_step"), "sufficient", "crisis"
        )
        harmony = SecretaryService.score_step(
            _step("rescue_entry_step"), "sufficient", "harmony"
        )
        assert crisis > harmony + 40  # +50 bonus


class TestBuildPlan:
    def test_empty_steps_returns_empty_list(self) -> None:
        result = SecretaryService.build_plan([], "sufficient", "harmony")
        assert result == []

    def test_blocked_steps_excluded_from_plan(self) -> None:
        steps = [
            _step("focus_step", "ready", step_id="1" * 32),
            _step("focus_step", "blocked", step_id="2" * 32),
        ]
        result = SecretaryService.build_plan(steps, "sufficient", "harmony")
        assert len(result) == 1
        assert result[0]["step_id"] == "1" * 32

    def test_plan_ordered_by_score_descending(self) -> None:
        steps = [
            _step("background_step", "ready", 15, step_id="1" * 32),
            _step("rescue_entry_step", "ready", 30, step_id="2" * 32),
            _step("focus_step", "ready", 45, step_id="3" * 32),
        ]
        result = SecretaryService.build_plan(steps, "sufficient", "harmony")
        assert result[0]["step_id"] == "2" * 32  # rescue_entry highest
        assert result[-1]["step_id"] == "1" * 32  # background lowest

    def test_plan_item_has_required_fields(self) -> None:
        result = SecretaryService.build_plan(
            [_step()], "sufficient", "harmony"
        )
        item = result[0]
        assert "order" in item
        assert "step_id" in item
        assert "title" in item
        assert "step_type" in item
        assert "energy_cost" in item
        assert "estimated_minutes" in item
        assert "score" in item

    def test_order_starts_at_one(self) -> None:
        result = SecretaryService.build_plan(
            [_step("focus_step", step_id="1" * 32), _step("background_step", step_id="2" * 32)],
            "sufficient", "harmony",
        )
        assert result[0]["order"] == 1
        assert result[1]["order"] == 2


class TestTotalMinutes:
    def test_sums_estimated_minutes(self) -> None:
        items = [
            {"estimated_minutes": 30},
            {"estimated_minutes": 45},
            {"estimated_minutes": 15},
        ]
        assert SecretaryService.total_minutes(items) == 90

    def test_none_minutes_treated_as_zero(self) -> None:
        items = [{"estimated_minutes": None}, {"estimated_minutes": 30}]
        assert SecretaryService.total_minutes(items) == 30

    def test_empty_list_returns_zero(self) -> None:
        assert SecretaryService.total_minutes([]) == 0
