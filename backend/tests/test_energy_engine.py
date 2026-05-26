"""
Unit tests for EnergyScoreEngine and BehavioralPolicyEngine.
Pure logic tests — no database, no HTTP.
TDD: these tests define the contract; implementation follows.
"""
import pytest

from app.services.energy import EnergyScoreEngine, EnergyState, IndirectSignals
from app.services.behavioral_policy import BehavioralPolicyEngine, PolicyAction


class TestEnergyStateNoHistory:
    def test_sufficient_at_70(self) -> None:
        assert EnergyScoreEngine.compute_state(70, None) == EnergyState.SUFFICIENT

    def test_sufficient_at_100(self) -> None:
        assert EnergyScoreEngine.compute_state(100, None) == EnergyState.SUFFICIENT

    def test_constrained_at_69(self) -> None:
        assert EnergyScoreEngine.compute_state(69, None) == EnergyState.CONSTRAINED

    def test_constrained_at_40(self) -> None:
        assert EnergyScoreEngine.compute_state(40, None) == EnergyState.CONSTRAINED

    def test_critical_at_39(self) -> None:
        assert EnergyScoreEngine.compute_state(39, None) == EnergyState.CRITICAL

    def test_critical_at_0(self) -> None:
        assert EnergyScoreEngine.compute_state(0, None) == EnergyState.CRITICAL


class TestHysteresisFromSufficient:
    # Down threshold: 70 - MARGIN(5) = 65
    def test_holds_at_boundary_65(self) -> None:
        # Exactly at the down threshold — stays sufficient
        assert EnergyScoreEngine.compute_state(65, EnergyState.SUFFICIENT) == EnergyState.SUFFICIENT

    def test_transitions_below_boundary_64(self) -> None:
        assert EnergyScoreEngine.compute_state(64, EnergyState.SUFFICIENT) == EnergyState.CONSTRAINED

    def test_deep_drop_goes_directly_to_critical(self) -> None:
        # Score 20 from SUFFICIENT is below both thresholds including hysteresis
        assert EnergyScoreEngine.compute_state(20, EnergyState.SUFFICIENT) == EnergyState.CRITICAL


class TestHysteresisFromConstrained:
    # Up threshold to sufficient:  70 + MARGIN(5) = 75
    # Down threshold to critical: 40 - MARGIN(5) = 35

    def test_transitions_up_at_75(self) -> None:
        assert EnergyScoreEngine.compute_state(75, EnergyState.CONSTRAINED) == EnergyState.SUFFICIENT

    def test_holds_below_75(self) -> None:
        assert EnergyScoreEngine.compute_state(74, EnergyState.CONSTRAINED) == EnergyState.CONSTRAINED

    def test_holds_at_boundary_35(self) -> None:
        # Exactly at the down threshold — stays constrained
        assert EnergyScoreEngine.compute_state(35, EnergyState.CONSTRAINED) == EnergyState.CONSTRAINED

    def test_transitions_down_at_34(self) -> None:
        assert EnergyScoreEngine.compute_state(34, EnergyState.CONSTRAINED) == EnergyState.CRITICAL


class TestHysteresisFromCritical:
    # Up threshold to constrained: 40 + MARGIN(5) = 45
    # Up threshold to sufficient:  70 + MARGIN(5) = 75

    def test_holds_below_45(self) -> None:
        assert EnergyScoreEngine.compute_state(44, EnergyState.CRITICAL) == EnergyState.CRITICAL

    def test_transitions_up_at_45(self) -> None:
        assert EnergyScoreEngine.compute_state(45, EnergyState.CRITICAL) == EnergyState.CONSTRAINED

    def test_deep_jump_goes_directly_to_sufficient(self) -> None:
        assert EnergyScoreEngine.compute_state(80, EnergyState.CRITICAL) == EnergyState.SUFFICIENT


class TestCheckinScoring:
    def test_perfect_score_is_100(self) -> None:
        assert EnergyScoreEngine.compute_from_checkin(sleep=5, mood=5, energy=5) == 100

    def test_minimum_score_is_20(self) -> None:
        # (1+1+1)/15 * 100 = 20
        assert EnergyScoreEngine.compute_from_checkin(sleep=1, mood=1, energy=1) == 20

    def test_midpoint_score_is_60(self) -> None:
        # (3+3+3)/15 * 100 = 60
        assert EnergyScoreEngine.compute_from_checkin(sleep=3, mood=3, energy=3) == 60

    def test_mixed_score(self) -> None:
        # (5+3+4)/15 * 100 = 80
        assert EnergyScoreEngine.compute_from_checkin(sleep=5, mood=3, energy=4) == 80

    def test_result_always_in_0_100(self) -> None:
        for v in range(1, 6):
            score = EnergyScoreEngine.compute_from_checkin(sleep=v, mood=v, energy=v)
            assert 0 <= score <= 100


class TestIndirectSignals:
    def test_morning_bonus_increases_score(self) -> None:
        base = 60
        signals = IndirectSignals(hour_of_day=8)
        assert EnergyScoreEngine.apply_indirect_signals(base, signals) > base

    def test_late_night_penalty_decreases_score(self) -> None:
        base = 60
        signals = IndirectSignals(hour_of_day=23)
        assert EnergyScoreEngine.apply_indirect_signals(base, signals) < base

    def test_abandoned_sessions_decrease_score(self) -> None:
        base = 70
        clean = IndirectSignals(hour_of_day=12)
        dirty = IndirectSignals(hour_of_day=12, abandoned_sessions=3)
        assert EnergyScoreEngine.apply_indirect_signals(base, dirty) < \
               EnergyScoreEngine.apply_indirect_signals(base, clean)

    def test_urge_events_decrease_score(self) -> None:
        base = 70
        clean = IndirectSignals(hour_of_day=12)
        urge = IndirectSignals(hour_of_day=12, urge_events_6h=2)
        assert EnergyScoreEngine.apply_indirect_signals(base, urge) < \
               EnergyScoreEngine.apply_indirect_signals(base, clean)

    def test_score_clamped_to_100(self) -> None:
        signals = IndirectSignals(hour_of_day=8)
        assert EnergyScoreEngine.apply_indirect_signals(100, signals) <= 100

    def test_score_clamped_to_0(self) -> None:
        signals = IndirectSignals(hour_of_day=23, abandoned_sessions=10, urge_events_6h=10, defer_events_24h=10)
        assert EnergyScoreEngine.apply_indirect_signals(0, signals) == 0

    def test_abandoned_sessions_cap(self) -> None:
        # 4 sessions and 100 sessions should hit the same cap
        base = 60
        cap_hit = IndirectSignals(hour_of_day=12, abandoned_sessions=4)
        over_cap = IndirectSignals(hour_of_day=12, abandoned_sessions=100)
        assert EnergyScoreEngine.apply_indirect_signals(base, cap_hit) == \
               EnergyScoreEngine.apply_indirect_signals(base, over_cap)


class TestModeSuggestion:
    def test_critical_state_suggests_crisis(self) -> None:
        assert EnergyScoreEngine.suggest_mode(EnergyState.CRITICAL, "harmony") == "crisis"

    def test_critical_in_crisis_no_suggestion(self) -> None:
        assert EnergyScoreEngine.suggest_mode(EnergyState.CRITICAL, "crisis") is None

    def test_sufficient_no_suggestion(self) -> None:
        assert EnergyScoreEngine.suggest_mode(EnergyState.SUFFICIENT, "harmony") is None

    def test_constrained_no_suggestion(self) -> None:
        assert EnergyScoreEngine.suggest_mode(EnergyState.CONSTRAINED, "achiever") is None


class TestBehavioralPolicy:
    def test_urge_event_interrupts(self) -> None:
        r = BehavioralPolicyEngine.evaluate("urge_event", energy_state=EnergyState.SUFFICIENT)
        assert r.action == PolicyAction.INTERRUPT
        assert r.delay_minutes > 0
        assert r.reflection_prompt

    def test_lapse_event_acknowledges(self) -> None:
        r = BehavioralPolicyEngine.evaluate("lapse_event", energy_state=EnergyState.SUFFICIENT)
        assert r.action == PolicyAction.ACKNOWLEDGE

    def test_recovery_event_reinforces(self) -> None:
        r = BehavioralPolicyEngine.evaluate("recovery_event", energy_state=EnergyState.SUFFICIENT)
        assert r.action == PolicyAction.REINFORCE

    def test_risk_window_alerts(self) -> None:
        r = BehavioralPolicyEngine.evaluate("risk_window", energy_state=EnergyState.SUFFICIENT)
        assert r.action == PolicyAction.ALERT

    def test_critical_energy_urge_gets_longer_delay(self) -> None:
        ok = BehavioralPolicyEngine.evaluate("urge_event", energy_state=EnergyState.SUFFICIENT)
        critical = BehavioralPolicyEngine.evaluate("urge_event", energy_state=EnergyState.CRITICAL)
        assert critical.delay_minutes >= ok.delay_minutes
