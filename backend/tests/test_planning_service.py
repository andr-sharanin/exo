"""
Unit tests for Phase 8: PlanningGoalService.
Pure function tests — no database.
"""
import pytest

from app.services.planning import PlanningGoalService


class TestHorizonOrder:
    def test_six_horizons_defined(self) -> None:
        assert len(PlanningGoalService.HORIZON_ORDER) == 6

    def test_vision_is_highest(self) -> None:
        assert PlanningGoalService.HORIZON_ORDER["vision"] == 0

    def test_daily_is_lowest(self) -> None:
        assert PlanningGoalService.HORIZON_ORDER["daily"] == 5

    def test_order_is_vision_annual_quarterly_monthly_weekly_daily(self) -> None:
        expected = ["vision", "annual", "quarterly", "monthly", "weekly", "daily"]
        actual = sorted(
            PlanningGoalService.HORIZON_ORDER,
            key=lambda h: PlanningGoalService.HORIZON_ORDER[h],
        )
        assert actual == expected


class TestHierarchyValidation:
    def test_vision_can_be_root(self) -> None:
        assert PlanningGoalService.is_valid_parent(None, "vision") is True

    def test_annual_can_be_root(self) -> None:
        assert PlanningGoalService.is_valid_parent(None, "annual") is True

    def test_vision_parent_of_annual(self) -> None:
        assert PlanningGoalService.is_valid_parent("vision", "annual") is True

    def test_annual_parent_of_quarterly(self) -> None:
        assert PlanningGoalService.is_valid_parent("annual", "quarterly") is True

    def test_quarterly_parent_of_monthly(self) -> None:
        assert PlanningGoalService.is_valid_parent("quarterly", "monthly") is True

    def test_monthly_parent_of_weekly(self) -> None:
        assert PlanningGoalService.is_valid_parent("monthly", "weekly") is True

    def test_weekly_parent_of_daily(self) -> None:
        assert PlanningGoalService.is_valid_parent("weekly", "daily") is True

    def test_annual_cannot_be_parent_of_vision(self) -> None:
        assert PlanningGoalService.is_valid_parent("annual", "vision") is False

    def test_same_level_is_invalid(self) -> None:
        assert PlanningGoalService.is_valid_parent("quarterly", "quarterly") is False

    def test_skip_level_is_valid(self) -> None:
        # vision → quarterly skips annual, still valid
        assert PlanningGoalService.is_valid_parent("vision", "quarterly") is True

    def test_daily_cannot_be_parent(self) -> None:
        # daily is the lowest level, cannot have children
        assert PlanningGoalService.is_valid_parent("daily", "daily") is False
