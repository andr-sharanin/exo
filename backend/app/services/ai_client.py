"""
AIClient — async LiteLLM wrapper with fallback chain and JSON parsing.

Usage:
    config = AIRouter.route(context)
    response = await AIClient.complete(messages, config)
    print(response.parsed)  # dict parsed from AI JSON output

In tests, patch litellm.acompletion with unittest.mock.AsyncMock.
"""
import json
import os
import re
import time
from dataclasses import dataclass

import litellm

from app.services.ai_router import AITierConfig


class AIClientError(Exception):
    pass


@dataclass
class AIResponse:
    content: str
    parsed: dict
    model_used: str
    tier: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    was_fallback: bool


def _inject_api_keys() -> None:
    """Copy DB-configured API keys into env so LiteLLM picks them up automatically.
    DB values override env only when non-empty. Called once per request cycle.
    """
    from app.services.config_service import ConfigService
    for env_name, cfg_key in [
        ("ANTHROPIC_API_KEY", "anthropic_api_key"),
        ("OPENAI_API_KEY", "openai_api_key"),
        ("OLLAMA_API_BASE", "ollama_base_url"),
    ]:
        # DB-loaded value injected at startup by ConfigService.sync_to_env()
        # Here we only ensure env is non-empty — actual sync happens on config write
        if not os.environ.get(env_name):
            default = ConfigService.get_default(cfg_key)
            if default:
                os.environ[env_name] = default


class AIClient:
    @classmethod
    async def complete(
        cls,
        messages: list[dict],
        config: AITierConfig,
    ) -> AIResponse:
        """
        Try primary model, then fallbacks in order.
        Returns AIResponse on first success.
        Raises AIClientError if all models fail.
        """
        models_to_try = [config.primary_model, *config.fallback_models]
        last_exc: Exception | None = None

        for i, model in enumerate(models_to_try):
            try:
                start = time.monotonic()
                kwargs: dict = dict(
                    model=model,
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                )
                if model.startswith("ollama/"):
                    kwargs["api_base"] = os.environ.get(
                        "OLLAMA_API_BASE", "http://localhost:11434"
                    )
                raw = await litellm.acompletion(**kwargs)
                latency_ms = int((time.monotonic() - start) * 1000)
                content: str = raw.choices[0].message.content
                parsed = cls._parse_json(content)

                return AIResponse(
                    content=content,
                    parsed=parsed,
                    model_used=model,
                    tier=config.tier.value,
                    prompt_tokens=raw.usage.prompt_tokens,
                    completion_tokens=raw.usage.completion_tokens,
                    latency_ms=latency_ms,
                    was_fallback=(i > 0),
                )
            except AIClientError:
                raise  # JSON parse failure — no point retrying same content
            except Exception as exc:
                last_exc = exc
                continue

        raise AIClientError(
            f"All {len(models_to_try)} models failed. Last: {last_exc}"
        ) from last_exc

    @staticmethod
    def _parse_json(content: str) -> dict:
        """Parse JSON from AI response; tolerates preamble text."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise AIClientError(
            f"Cannot parse AI response as JSON. First 200 chars: {content[:200]!r}"
        )
