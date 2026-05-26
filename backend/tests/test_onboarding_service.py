"""
Unit tests for Phase 5: OnboardingService.
Written FIRST (TDD) — these define the contract before implementation.
No database I/O — pure function tests only.
"""
import pytest

from app.services.onboarding import OnboardingMode, OnboardingService

# Quick mode covers 8 dimensions (failure_response_pattern requires deep mode)
QUICK_DIMS = {
    "focus_stability",
    "task_handling_style",
    "decision_style",
    "overload_threshold",
    "interruption_behavior",
    "clarity_strategy",
    "execution_pattern",
    "help_seeking_behavior",
}
# Deep mode adds the 9th
DEEP_DIMS = QUICK_DIMS | {"failure_response_pattern"}
ALL_DIMS = DEEP_DIMS


class TestQuestionBank:
    def test_quick_mode_has_exactly_7_questions(self) -> None:
        questions = OnboardingService.get_questions(OnboardingMode.QUICK)
        assert len(questions) == 7

    def test_deep_mode_has_more_questions_than_quick(self) -> None:
        quick = OnboardingService.get_questions(OnboardingMode.QUICK)
        deep = OnboardingService.get_questions(OnboardingMode.DEEP)
        assert len(deep) > len(quick)

    def test_quick_mode_covers_eight_dimensions(self) -> None:
        questions = OnboardingService.get_questions(OnboardingMode.QUICK)
        covered: set[str] = set()
        for q in questions:
            for opt in q.options:
                covered.update(opt.scores.keys())
        assert covered == QUICK_DIMS

    def test_deep_mode_covers_all_nine_dimensions(self) -> None:
        questions = OnboardingService.get_questions(OnboardingMode.DEEP)
        covered: set[str] = set()
        for q in questions:
            for opt in q.options:
                covered.update(opt.scores.keys())
        assert DEEP_DIMS.issubset(covered)

    def test_each_question_has_at_least_two_options(self) -> None:
        for mode in OnboardingMode:
            for q in OnboardingService.get_questions(mode):
                assert len(q.options) >= 2, (
                    f"Question {q.question_id!r} has fewer than 2 options"
                )

    def test_option_ids_are_unique_within_question(self) -> None:
        for mode in OnboardingMode:
            for q in OnboardingService.get_questions(mode):
                ids = [o.option_id for o in q.options]
                assert len(ids) == len(set(ids)), (
                    f"Duplicate option_ids in {q.question_id!r}"
                )

    def test_question_ids_are_unique_across_bank(self) -> None:
        deep_qs = OnboardingService.get_questions(OnboardingMode.DEEP)
        ids = [q.question_id for q in deep_qs]
        assert len(ids) == len(set(ids))


class TestScoreAnswers:
    def _get_q(self, question_id: str):
        all_qs = OnboardingService.get_questions(OnboardingMode.DEEP)
        return next(q for q in all_qs if q.question_id == question_id)

    def _opt_for(self, question_id: str, dimension: str, value: str) -> str:
        q = self._get_q(question_id)
        opt = next(
            o for o in q.options if o.scores.get(dimension) == value
        )
        return opt.option_id

    def test_high_focus_stability_from_q_focus(self) -> None:
        opt = self._opt_for("Q_FOCUS", "focus_stability", "high")
        result = OnboardingService.score_answers({"Q_FOCUS": opt})
        assert result["focus_stability"] == "high"

    def test_sequential_task_handling_from_q_tasks(self) -> None:
        opt = self._opt_for("Q_TASKS", "task_handling_style", "sequential")
        result = OnboardingService.score_answers({"Q_TASKS": opt})
        assert result["task_handling_style"] == "sequential"

    def test_fast_decision_style_from_q_decision(self) -> None:
        opt = self._opt_for("Q_DECISION", "decision_style", "fast")
        result = OnboardingService.score_answers({"Q_DECISION": opt})
        assert result["decision_style"] == "fast"

    def test_q_stuck_scores_two_dimensions(self) -> None:
        q = self._get_q("Q_STUCK")
        multi_opt = next(o for o in q.options if len(o.scores) >= 2)
        result = OnboardingService.score_answers({"Q_STUCK": multi_opt.option_id})
        assert "clarity_strategy" in result
        assert "help_seeking_behavior" in result

    def test_deep_q_decision2_overwrites_q_decision(self) -> None:
        # Quick: Q_DECISION → fast; Deep: Q_DECISION2 → deliberate
        fast_opt = self._opt_for("Q_DECISION", "decision_style", "fast")
        delib_opt = self._opt_for("Q_DECISION2", "decision_style", "deliberate")
        result = OnboardingService.score_answers({
            "Q_DECISION": fast_opt,
            "Q_DECISION2": delib_opt,
        })
        assert result["decision_style"] == "deliberate"

    def test_overwrite_order_is_canonical_not_dict_insertion(self) -> None:
        # Submitting in reverse order still gives deep question priority
        fast_opt = self._opt_for("Q_DECISION", "decision_style", "fast")
        delib_opt = self._opt_for("Q_DECISION2", "decision_style", "deliberate")
        result = OnboardingService.score_answers({
            "Q_DECISION2": delib_opt,
            "Q_DECISION": fast_opt,
        })
        # Q_DECISION2 is later in canonical order → must win
        assert result["decision_style"] == "deliberate"

    def test_unknown_question_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown question"):
            OnboardingService.score_answers({"NONEXISTENT": "A"})

    def test_unknown_option_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown option"):
            OnboardingService.score_answers({"Q_FOCUS": "Z"})


class TestComputeProfile:
    def _achiever_scores(self) -> dict[str, str]:
        return {
            "focus_stability": "high",
            "task_handling_style": "sequential",
            "decision_style": "fast",
            "overload_threshold": "high",
            "interruption_behavior": "adaptive",
            "clarity_strategy": "acting",
            "execution_pattern": "sprint",
            "help_seeking_behavior": "reactive",
            "failure_response_pattern": "bounce_back",
        }

    def test_profile_data_has_all_nine_dimensions(self) -> None:
        profile_data, _ = OnboardingService.compute_profile(self._achiever_scores())
        assert set(profile_data.keys()) == ALL_DIMS

    def test_computed_defaults_has_three_required_fields(self) -> None:
        _, defaults = OnboardingService.compute_profile(self._achiever_scores())
        assert "dominant_mode" in defaults
        assert "energy_archetype" in defaults
        assert "recommended_session_length" in defaults

    def test_achiever_mode_from_high_focus_fast_decision(self) -> None:
        _, defaults = OnboardingService.compute_profile(self._achiever_scores())
        assert defaults["dominant_mode"] == "achiever"

    def test_recovery_mode_from_low_focus_low_threshold(self) -> None:
        scores = self._achiever_scores() | {
            "focus_stability": "low",
            "overload_threshold": "low",
        }
        _, defaults = OnboardingService.compute_profile(scores)
        assert defaults["dominant_mode"] == "recovery"

    def test_recovery_mode_from_avoidant_freeze_combo(self) -> None:
        scores = self._achiever_scores() | {
            "decision_style": "avoidant",
            "failure_response_pattern": "freeze",
            "focus_stability": "medium",
            "overload_threshold": "medium",
        }
        _, defaults = OnboardingService.compute_profile(scores)
        assert defaults["dominant_mode"] == "recovery"

    def test_creative_mode_from_burst_parallel(self) -> None:
        scores = self._achiever_scores() | {
            "execution_pattern": "burst",
            "task_handling_style": "parallel",
            "focus_stability": "medium",
            "decision_style": "deliberate",
        }
        _, defaults = OnboardingService.compute_profile(scores)
        assert defaults["dominant_mode"] == "creative"

    def test_clarity_mode_from_writing_deliberate(self) -> None:
        scores = self._achiever_scores() | {
            "clarity_strategy": "writing",
            "decision_style": "deliberate",
            "focus_stability": "medium",
        }
        _, defaults = OnboardingService.compute_profile(scores)
        assert defaults["dominant_mode"] == "clarity"

    def test_session_length_90_for_high_focus_marathon(self) -> None:
        scores = self._achiever_scores() | {"execution_pattern": "marathon"}
        _, defaults = OnboardingService.compute_profile(scores)
        assert defaults["recommended_session_length"] == 90

    def test_session_length_25_for_low_focus(self) -> None:
        scores = self._achiever_scores() | {"focus_stability": "low"}
        _, defaults = OnboardingService.compute_profile(scores)
        assert defaults["recommended_session_length"] == 25

    def test_session_length_45_for_medium_focus(self) -> None:
        scores = self._achiever_scores() | {"focus_stability": "medium"}
        _, defaults = OnboardingService.compute_profile(scores)
        assert defaults["recommended_session_length"] == 45

    def test_missing_dimensions_get_sensible_defaults(self) -> None:
        # Pass only one dimension — rest should be filled with defaults
        profile_data, _ = OnboardingService.compute_profile({"focus_stability": "high"})
        assert set(profile_data.keys()) == ALL_DIMS
        assert profile_data["focus_stability"] == "high"


class TestRecalibrateFromBehavior:
    def _base(self) -> dict:
        return {
            "dominant_mode": "achiever",
            "energy_archetype": "variable",
            "recommended_session_length": 45,
        }

    def test_high_urge_events_shifts_mode_to_recovery(self) -> None:
        updated = OnboardingService.recalibrate_defaults(
            self._base(),
            urge_events_last_30d=12,
            abandoned_sessions_last_30d=0,
            completed_sessions_last_30d=5,
        )
        assert updated["dominant_mode"] == "recovery"

    def test_high_abandonment_rate_shifts_mode_to_recovery(self) -> None:
        # 15 abandoned out of 20 total = 75% abandonment rate
        updated = OnboardingService.recalibrate_defaults(
            self._base(),
            urge_events_last_30d=0,
            abandoned_sessions_last_30d=15,
            completed_sessions_last_30d=5,
        )
        assert updated["dominant_mode"] == "recovery"

    def test_healthy_behavior_preserves_original_mode(self) -> None:
        updated = OnboardingService.recalibrate_defaults(
            self._base(),
            urge_events_last_30d=2,
            abandoned_sessions_last_30d=2,
            completed_sessions_last_30d=20,
        )
        assert updated["dominant_mode"] == "achiever"

    def test_recalibrate_returns_copy_not_mutation(self) -> None:
        base = self._base()
        OnboardingService.recalibrate_defaults(
            base,
            urge_events_last_30d=20,
            abandoned_sessions_last_30d=0,
            completed_sessions_last_30d=0,
        )
        assert base["dominant_mode"] == "achiever"
