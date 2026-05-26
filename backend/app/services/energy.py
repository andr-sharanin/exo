"""
EnergyScoreEngine — composite energy scoring with hysteresis stabilisation.

Pure stateless class methods. No database I/O — all inputs are explicit.
"""
from dataclasses import dataclass
from enum import StrEnum


class EnergyState(StrEnum):
    SUFFICIENT = "sufficient"    # 70–100 — full capacity
    CONSTRAINED = "constrained"  # 40–69 — reduced but functional
    CRITICAL = "critical"        # 0–39  — minimum viable mode


@dataclass(frozen=True)
class IndirectSignals:
    """Computed signals that adjust the check-in base score."""
    hour_of_day: int = 12
    abandoned_sessions: int = 0
    urge_events_6h: int = 0
    defer_events_24h: int = 0


class EnergyScoreEngine:
    SUFFICIENT_THRESHOLD: int = 70
    CONSTRAINED_THRESHOLD: int = 40
    HYSTERESIS_MARGIN: int = 5

    @classmethod
    def compute_from_checkin(cls, *, sleep: int, mood: int, energy: int) -> int:
        """Convert three 1–5 Likert responses to a 0–100 base score."""
        return max(0, min(100, round(((sleep + mood + energy) / 15.0) * 100)))

    @classmethod
    def compute_state(cls, score: int, previous_state: EnergyState | None) -> EnergyState:
        """
        Determine energy state with hysteresis to prevent rapid oscillation.

        Without previous_state (first reading), applies raw thresholds.
        With previous_state, requires crossing threshold ± MARGIN to switch.

          Transition         Trigger condition
          sufficient → lower  score < 70 - 5 = 65
          constrained → up    score >= 70 + 5 = 75
          constrained → down  score <  40 - 5 = 35
          critical → up       score >= 40 + 5 = 45
        """
        high = cls.SUFFICIENT_THRESHOLD   # 70
        low = cls.CONSTRAINED_THRESHOLD   # 40
        m = cls.HYSTERESIS_MARGIN         # 5

        if previous_state is None:
            if score >= high:
                return EnergyState.SUFFICIENT
            if score >= low:
                return EnergyState.CONSTRAINED
            return EnergyState.CRITICAL

        if previous_state == EnergyState.SUFFICIENT:
            if score < high - m:                              # < 65: leave sufficient
                return EnergyState.CONSTRAINED if score >= low - m else EnergyState.CRITICAL
            return EnergyState.SUFFICIENT

        if previous_state == EnergyState.CONSTRAINED:
            if score >= high + m:   # >= 75: enter sufficient
                return EnergyState.SUFFICIENT
            if score < low - m:     # <  35: enter critical
                return EnergyState.CRITICAL
            return EnergyState.CONSTRAINED

        # CRITICAL
        if score >= high + m:   # >= 75: jump directly to sufficient
            return EnergyState.SUFFICIENT
        if score >= low + m:    # >= 45: enter constrained
            return EnergyState.CONSTRAINED
        return EnergyState.CRITICAL

    @classmethod
    def apply_indirect_signals(cls, base_score: int, signals: IndirectSignals) -> int:
        """
        Adjust base score with indirect behavioural signals.
        Each signal is capped so no single factor dominates.

          Signal                    Weight   Cap
          Morning window (6–12h)    +8       —
          Late night   (22–4h)      −10      —
          Abandoned sessions/24h    −5 each  −20
          Urge events / 6h          −8 each  −24
          Defer events / 24h        −3 each  −15
        """
        delta = 0

        h = signals.hour_of_day
        if 6 <= h <= 12:
            delta += 8
        elif h >= 22 or h <= 4:
            delta -= 10

        delta -= min(signals.abandoned_sessions * 5, 20)
        delta -= min(signals.urge_events_6h * 8, 24)
        delta -= min(signals.defer_events_24h * 3, 15)

        return max(0, min(100, base_score + delta))

    @classmethod
    def suggest_mode(cls, state: EnergyState, current_mode: str) -> str | None:
        """Proactively suggest a mode switch when energy state warrants it."""
        if state == EnergyState.CRITICAL and current_mode != "crisis":
            return "crisis"
        return None
