"""
PlanningGoalService — pure hierarchy logic for planning goals.

Six horizons in descending order:
  vision(0) → annual(1) → quarterly(2) → monthly(3) → weekly(4) → daily(5)

A child's horizon level must be strictly greater than its parent's.
"""


class PlanningGoalService:
    HORIZON_ORDER: dict[str, int] = {
        "vision": 0,
        "annual": 1,
        "quarterly": 2,
        "monthly": 3,
        "weekly": 4,
        "daily": 5,
    }

    @classmethod
    def is_valid_parent(cls, parent_horizon: str | None, child_horizon: str) -> bool:
        """Return True if parent_horizon is a valid parent for child_horizon.

        None parent is always valid (root goal).
        Parent level must be strictly less than child level.
        """
        if parent_horizon is None:
            return True
        parent_level = cls.HORIZON_ORDER.get(parent_horizon)
        child_level = cls.HORIZON_ORDER.get(child_horizon)
        if parent_level is None or child_level is None:
            return False
        return parent_level < child_level
