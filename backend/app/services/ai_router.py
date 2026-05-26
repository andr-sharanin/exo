"""
AIRouter — routes AI requests to the appropriate tier based on context.

Three tiers:
  MECHANICAL  (Tier 1) — Claude Haiku: classification, extraction, formatting
  ANALYTICAL  (Tier 2) — Claude Sonnet: reasoning, patterns, advisory
  STRATEGIC   (Tier 3) — Claude Opus: deep reasoning, decision support

Routing priority (highest wins):
  1. budget < 10%       → MECHANICAL
  2. energy = critical  → MECHANICAL
  3. stage = CLASSIFICATION / CAPTURE → MECHANICAL
  4. stage = REASON / DECIDE + complexity=high + energy=sufficient → STRATEGIC
  5. stage = REASON / DECIDE + complexity=high + energy=constrained → ANALYTICAL
  6. stage = REASON / DECIDE + complexity=low  → MECHANICAL
  7. everything else    → ANALYTICAL
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AITier(StrEnum):
    MECHANICAL = "mechanical"
    ANALYTICAL = "analytical"
    STRATEGIC = "strategic"


class PipelineStage(StrEnum):
    CAPTURE = "capture"
    CLASSIFICATION = "classification"
    REASON = "reason"
    DECIDE = "decide"
    ADVISORY = "advisory"


@dataclass
class AIRoutingContext:
    stage: PipelineStage
    complexity: str = "medium"          # "low" | "medium" | "high"
    energy_state: str = "sufficient"    # "sufficient" | "constrained" | "critical"
    system_mode: str = "harmony"        # from SystemModeType
    budget_remaining_pct: float = 1.0   # 0.0–1.0


@dataclass(frozen=True)
class AITierConfig:
    tier: AITier
    primary_model: str
    fallback_models: list[str]
    max_tokens: int
    temperature: float


_TIER_CONFIGS: dict[AITier, AITierConfig] = {
    AITier.MECHANICAL: AITierConfig(
        tier=AITier.MECHANICAL,
        primary_model="claude-haiku-4-5-20251001",
        fallback_models=["gpt-4o-mini", "ollama/llama3.2"],
        max_tokens=1024,
        temperature=0.1,
    ),
    AITier.ANALYTICAL: AITierConfig(
        tier=AITier.ANALYTICAL,
        primary_model="claude-sonnet-4-6",
        fallback_models=["gpt-4o", "claude-haiku-4-5-20251001"],
        max_tokens=4096,
        temperature=0.3,
    ),
    AITier.STRATEGIC: AITierConfig(
        tier=AITier.STRATEGIC,
        primary_model="claude-opus-4-7",
        fallback_models=["claude-sonnet-4-6", "gpt-4o"],
        max_tokens=8192,
        temperature=0.5,
    ),
}


class AIRouter:
    @classmethod
    def route(cls, context: AIRoutingContext) -> AITierConfig:
        tier = cls._select_tier(context)
        return _TIER_CONFIGS[tier]

    @classmethod
    def get_config(cls, tier: AITier) -> AITierConfig:
        return _TIER_CONFIGS[tier]

    @classmethod
    def _select_tier(cls, ctx: AIRoutingContext) -> AITier:
        # Budget override — always use cheapest tier when budget is nearly exhausted
        if ctx.budget_remaining_pct < 0.10:
            return AITier.MECHANICAL

        # Energy override — critical energy forbids heavy AI inference
        if ctx.energy_state == "critical":
            return AITier.MECHANICAL

        # Fast-track stages that never need deep reasoning
        if ctx.stage in (PipelineStage.CAPTURE, PipelineStage.CLASSIFICATION):
            return AITier.MECHANICAL

        # Reason and Decide: complexity + energy determine tier
        if ctx.stage in (PipelineStage.REASON, PipelineStage.DECIDE):
            if ctx.complexity == "low":
                return AITier.MECHANICAL
            if ctx.complexity == "high" and ctx.energy_state == "sufficient":
                return AITier.STRATEGIC
            return AITier.ANALYTICAL  # medium complexity, or high+constrained

        # Advisory and everything else
        return AITier.ANALYTICAL
