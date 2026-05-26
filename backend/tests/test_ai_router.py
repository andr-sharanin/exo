"""
Unit tests for Phase 6: AIRouter — tier selection logic.
Written FIRST (TDD). Pure function tests, no database or network I/O.
"""
import pytest

from app.services.ai_router import AIRouter, AIRoutingContext, AITier, PipelineStage


class TestTierSelectionByStage:
    def test_classification_always_routes_mechanical(self) -> None:
        ctx = AIRoutingContext(stage=PipelineStage.CLASSIFICATION)
        assert AIRouter.route(ctx).tier == AITier.MECHANICAL

    def test_capture_defaults_to_mechanical(self) -> None:
        ctx = AIRoutingContext(stage=PipelineStage.CAPTURE)
        assert AIRouter.route(ctx).tier == AITier.MECHANICAL

    def test_reason_medium_complexity_routes_analytical(self) -> None:
        ctx = AIRoutingContext(stage=PipelineStage.REASON, complexity="medium")
        assert AIRouter.route(ctx).tier == AITier.ANALYTICAL

    def test_reason_low_complexity_routes_mechanical(self) -> None:
        ctx = AIRoutingContext(stage=PipelineStage.REASON, complexity="low")
        assert AIRouter.route(ctx).tier == AITier.MECHANICAL

    def test_reason_high_complexity_sufficient_routes_strategic(self) -> None:
        ctx = AIRoutingContext(
            stage=PipelineStage.REASON, complexity="high", energy_state="sufficient"
        )
        assert AIRouter.route(ctx).tier == AITier.STRATEGIC

    def test_decide_high_complexity_sufficient_routes_strategic(self) -> None:
        ctx = AIRoutingContext(
            stage=PipelineStage.DECIDE, complexity="high", energy_state="sufficient"
        )
        assert AIRouter.route(ctx).tier == AITier.STRATEGIC

    def test_decide_medium_complexity_routes_analytical(self) -> None:
        ctx = AIRoutingContext(stage=PipelineStage.DECIDE, complexity="medium")
        assert AIRouter.route(ctx).tier == AITier.ANALYTICAL

    def test_advisory_routes_analytical_regardless_of_complexity(self) -> None:
        for complexity in ("low", "medium", "high"):
            ctx = AIRoutingContext(stage=PipelineStage.ADVISORY, complexity=complexity)
            assert AIRouter.route(ctx).tier == AITier.ANALYTICAL, (
                f"Expected ANALYTICAL for advisory complexity={complexity}"
            )


class TestEnergyOverrides:
    def test_critical_energy_forces_mechanical(self) -> None:
        ctx = AIRoutingContext(
            stage=PipelineStage.REASON, complexity="high", energy_state="critical"
        )
        assert AIRouter.route(ctx).tier == AITier.MECHANICAL

    def test_critical_energy_overrides_advisory(self) -> None:
        ctx = AIRoutingContext(stage=PipelineStage.ADVISORY, energy_state="critical")
        assert AIRouter.route(ctx).tier == AITier.MECHANICAL

    def test_constrained_energy_blocks_strategic(self) -> None:
        # High complexity but constrained energy — no strategic tier
        ctx = AIRoutingContext(
            stage=PipelineStage.REASON, complexity="high", energy_state="constrained"
        )
        assert AIRouter.route(ctx).tier == AITier.ANALYTICAL

    def test_constrained_energy_does_not_downgrade_analytical(self) -> None:
        ctx = AIRoutingContext(
            stage=PipelineStage.REASON, complexity="medium", energy_state="constrained"
        )
        assert AIRouter.route(ctx).tier == AITier.ANALYTICAL

    def test_sufficient_energy_allows_strategic(self) -> None:
        ctx = AIRoutingContext(
            stage=PipelineStage.DECIDE, complexity="high", energy_state="sufficient"
        )
        assert AIRouter.route(ctx).tier == AITier.STRATEGIC


class TestBudgetOverride:
    def test_very_low_budget_forces_mechanical(self) -> None:
        ctx = AIRoutingContext(
            stage=PipelineStage.REASON, complexity="high",
            energy_state="sufficient", budget_remaining_pct=0.05,
        )
        assert AIRouter.route(ctx).tier == AITier.MECHANICAL

    def test_exactly_10pct_budget_forces_mechanical(self) -> None:
        ctx = AIRoutingContext(
            stage=PipelineStage.ADVISORY, budget_remaining_pct=0.09,
        )
        assert AIRouter.route(ctx).tier == AITier.MECHANICAL

    def test_above_10pct_budget_does_not_override(self) -> None:
        ctx = AIRoutingContext(
            stage=PipelineStage.ADVISORY, budget_remaining_pct=0.15,
        )
        assert AIRouter.route(ctx).tier == AITier.ANALYTICAL


class TestTierConfigs:
    def test_mechanical_uses_haiku_as_primary(self) -> None:
        config = AIRouter.get_config(AITier.MECHANICAL)
        assert "haiku" in config.primary_model.lower()

    def test_analytical_uses_sonnet_as_primary(self) -> None:
        config = AIRouter.get_config(AITier.ANALYTICAL)
        assert "sonnet" in config.primary_model.lower()

    def test_strategic_uses_opus_as_primary(self) -> None:
        config = AIRouter.get_config(AITier.STRATEGIC)
        assert "opus" in config.primary_model.lower()

    def test_all_tiers_have_at_least_one_fallback(self) -> None:
        for tier in AITier:
            config = AIRouter.get_config(tier)
            assert len(config.fallback_models) >= 1, (
                f"Tier {tier} has no fallback models"
            )

    def test_mechanical_has_lowest_max_tokens(self) -> None:
        mech = AIRouter.get_config(AITier.MECHANICAL)
        anal = AIRouter.get_config(AITier.ANALYTICAL)
        strat = AIRouter.get_config(AITier.STRATEGIC)
        assert mech.max_tokens <= anal.max_tokens <= strat.max_tokens
