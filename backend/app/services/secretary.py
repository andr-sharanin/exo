"""
SecretaryService — pure scoring logic for daily plan generation.
No database or AI calls — all inputs come as plain dicts from repos.

Scoring:
  Base: rescue_entry_step=100, focus_step=60, background_step=20
  Energy modifier: sufficient+high→+15, sufficient+low→-5,
                   critical+high→-20, critical+low→+15
  Mode modifier: achiever+focus→+20, recovery+focus→-20, crisis+rescue→+50
  Blocked: -1000 (excluded from plan)
"""


class SecretaryService:
    _BASE_SCORES: dict[str, float] = {
        "rescue_entry_step": 100.0,
        "focus_step": 60.0,
        "background_step": 20.0,
    }

    @classmethod
    def derive_energy_cost(cls, estimated_minutes: int | None) -> str:
        if estimated_minutes is None or estimated_minutes <= 25:
            return "low"
        if estimated_minutes <= 60:
            return "medium"
        return "high"

    @classmethod
    def score_step(cls, step: dict, energy_state: str, system_mode: str) -> float:
        if step.get("execution_readiness") == "blocked":
            return -1000.0
        step_type = step.get("step_type", "focus_step")
        base = cls._BASE_SCORES.get(step_type, 40.0)
        energy_cost = cls.derive_energy_cost(step.get("estimated_minutes"))
        return base + cls._energy_modifier(energy_cost, energy_state) + cls._mode_modifier(step_type, system_mode)

    @classmethod
    def _energy_modifier(cls, energy_cost: str, energy_state: str) -> float:
        if energy_state == "sufficient":
            if energy_cost == "high":
                return 15.0
            if energy_cost == "low":
                return -5.0
        elif energy_state == "critical":
            if energy_cost == "high":
                return -20.0
            if energy_cost == "low":
                return 15.0
        return 0.0

    @classmethod
    def _mode_modifier(cls, step_type: str, system_mode: str) -> float:
        if system_mode == "achiever" and step_type == "focus_step":
            return 20.0
        if system_mode == "recovery" and step_type == "focus_step":
            return -20.0
        if system_mode == "crisis" and step_type == "rescue_entry_step":
            return 50.0
        return 0.0

    @classmethod
    def build_plan(
        cls, steps: list[dict], energy_state: str, system_mode: str
    ) -> list[dict]:
        scored = []
        for step in steps:
            score = cls.score_step(step, energy_state, system_mode)
            if score < 0:
                continue
            scored.append((score, step))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "order": order,
                "step_id": step["id"],
                "title": step["title"],
                "step_type": step["step_type"],
                "energy_cost": cls.derive_energy_cost(step.get("estimated_minutes")),
                "estimated_minutes": step.get("estimated_minutes"),
                "score": score,
            }
            for order, (score, step) in enumerate(scored, start=1)
        ]

    @classmethod
    def total_minutes(cls, plan_items: list[dict]) -> int:
        return sum(item.get("estimated_minutes") or 0 for item in plan_items)
